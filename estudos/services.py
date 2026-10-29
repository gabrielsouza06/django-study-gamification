from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from .models import SessaoEstudo, PerfilUsuario, Conquista, ConquistaUsuario, ArvoreFoco

class GamificationService:
    @staticmethod
    @transaction.atomic
    def processar_recompensas_sessao(sessao):
        if sessao.estado != 'CONCLUIDO' or sessao.duracao_minutos <= 0 or not sessao.user:
            return

        user = sessao.user
        perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
        hoje = timezone.now().date()

        # 1. Atualizar Streaks
        if perfil.ultimo_dia_estudado != hoje:
            if perfil.ultimo_dia_estudado == hoje - timedelta(days=1):
                perfil.streak_atual += 1
            else:
                perfil.streak_atual = 1
            perfil.ultimo_dia_estudado = hoje
            if perfil.streak_atual > perfil.maior_streak:
                perfil.maior_streak = perfil.streak_atual
            perfil.save()

        # 2. Cultivar Árvore de Foco Idempotente
        if not hasattr(sessao, 'arvore'):
            tipo = 'Carvalho Vigoroso' if sessao.duracao_minutos >= 50 else 'Pequeno Broto'
            icone = 'bi-tree-fill' if sessao.duracao_minutos >= 50 else 'bi-flower1'
            ArvoreFoco.objects.create(
                user=user,
                sessao=sessao,
                tipo_arvore=tipo,
                icone_css=icone
            )

        # 3. Avaliar Desbloqueio de Conquistas
        GamificationService.avaliar_conquistas(user, perfil)

    @staticmethod
    def avaliar_conquistas(user, perfil):
        sessoes = SessaoEstudo.objects.filter(user=user, estado='CONCLUIDO')
        total_minutos = sessoes.aggregate(Sum('duracao_minutos'))['duracao_minutos__sum'] or 0
        total_horas = total_minutos / 60.0
        ciclos_pomodoro = sessoes.filter(metodo='POMODORO').aggregate(Sum('ciclos_concluidos'))['ciclos_concluidos__sum'] or 0

        # Mapeamento de Regras
        regras = {
            'PRIMEIRO_PASSO': sessoes.exists(),
            'PRIMEIRA_MARATONA': any(
                (sessoes.filter(data__date=d).aggregate(Sum('duracao_minutos'))['duracao_minutos__sum'] or 0) >= 300
                for d in sessoes.values_list('data__date', flat=True).distinct()
            ),
            'MESTRE_POMODORO': ciclos_pomodoro >= 50,
            'FOCO_DE_ACO': perfil.streak_atual >= 7,
            'ESTUDANTE_DEDICADO': total_horas >= 25,
            'CENTENARIO': total_horas >= 100,
        }

        for cod, elegivel in regras.items():
            if elegivel:
                conquista = Conquista.objects.filter(codigo=cod).first()
                if conquista:
                    ConquistaUsuario.objects.get_or_create(user=user, conquista=conquista)

class TimerService:
    @staticmethod
    def iniciar_nova_sessao(user, data):
        metodo = data.get('metodo', 'POMODORO')
        foco = int(data.get('tempo_foco_min', 25))
        d_curto = int(data.get('tempo_descanso_curto_min', 5))
        d_longo = int(data.get('tempo_descanso_longo_min', 15))
        ciclos = int(data.get('total_ciclos_planejados', 4))

        if metodo == 'POMODORO':
            foco, d_curto, d_longo, ciclos = 25, 5, 15, 4
        elif metodo == 'CINQUENTA_DEZ':
            foco, d_curto, d_longo, ciclos = 50, 10, 20, 3

        agora = timezone.now()
        duracao_inicial_seg = foco * 60

        sessao = SessaoEstudo.objects.create(
            user=user,
            materia=data.get('materia'),
            assunto=data.get('assunto', ''),
            disciplina_id=data.get('disciplina') or None,
            avaliacao_id=data.get('avaliacao') or None,
            metodo=metodo,
            tempo_foco_min=foco,
            tempo_descanso_curto_min=d_curto,
            tempo_descanso_longo_min=d_longo,
            total_ciclos_planejados=ciclos,
            estado='EM_ANDAMENTO',
            etapa_atual='FOCO',
            horario_inicio=agora,
            horario_termino_previsto=agora + timedelta(seconds=duracao_inicial_seg),
            tempo_restante_segundos=duracao_inicial_seg
        )
        return sessao

    @staticmethod
    def sincronizar_estado(sessao):
        agora = timezone.now()
        if sessao.estado in ['EM_ANDAMENTO', 'EM_DESCANSO']:
            if agora >= sessao.horario_termino_previsto:
                TimerService.avancar_etapa(sessao)
            else:
                delta = (sessao.horario_termino_previsto - agora).total_seconds()
                sessao.tempo_restante_segundos = max(0, int(delta))
                sessao.save(update_fields=['tempo_restante_segundos'])
        return sessao

    @staticmethod
    @transaction.atomic
    def avancar_etapa(sessao):
        agora = timezone.now()
        if sessao.etapa_atual == 'FOCO':
            sessao.segundos_foco_acumulados += (sessao.tempo_foco_min * 60)
            sessao.ciclos_concluidos += 1
            if sessao.ciclos_concluidos >= sessao.total_ciclos_planejados:
                return TimerService.finalizar(sessao)

            if sessao.ciclos_concluidos % 4 == 0 and sessao.tempo_descanso_longo_min > 0:
                sessao.etapa_atual = 'DESCANSO_LONGO'
                duracao = sessao.tempo_descanso_longo_min * 60
            else:
                sessao.etapa_atual = 'DESCANSO_CURTO'
                duracao = sessao.tempo_descanso_curto_min * 60
            sessao.estado = 'EM_DESCANSO'
        else:
            sessao.etapa_atual = 'FOCO'
            duracao = sessao.tempo_foco_min * 60
            sessao.estado = 'EM_ANDAMENTO'

        sessao.tempo_restante_segundos = duracao
        sessao.horario_termino_previsto = agora + timedelta(seconds=duracao)
        sessao.save()
        return sessao

    @staticmethod
    @transaction.atomic
    def finalizar(sessao, antecipado=False):
        if antecipado and sessao.etapa_atual == 'FOCO' and sessao.horario_termino_previsto:
            agora = timezone.now()
            tempo_restante = max(0, int((sessao.horario_termino_previsto - agora).total_seconds()))
            foco_parcial = max(0, (sessao.tempo_foco_min * 60) - tempo_restante)
            sessao.segundos_foco_acumulados += foco_parcial

        sessao.estado = 'CONCLUIDO'
        sessao.duracao_minutos = round(sessao.segundos_foco_acumulados / 60)
        sessao.save()

        # Processar recompensas no módulo de Gamificação
        GamificationService.processar_recompensas_sessao(sessao)
        return sessao

    @staticmethod
    @transaction.atomic
    def cancelar(sessao):
        sessao.estado = 'CANCELADO'
        sessao.duracao_minutos = 0
        sessao.save()
        return sessao