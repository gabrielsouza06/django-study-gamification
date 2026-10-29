from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import SessaoEstudo, PerfilUsuario, Conquista, ConquistaUsuario, ArvoreFoco, Disciplina
from .services import TimerService, GamificationService

class GamificationAndTimerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='gabriel', password='123')
        self.disciplina = Disciplina.objects.create(user=self.user, nome='Cálculo I')
        Conquista.objects.create(codigo='PRIMEIRO_PASSO', nome='Primeiro Passo', descricao='Concluir primeira sessão', criterio='1 sessão')

    def test_conclusao_sessao_e_recompensas_idempotentes(self):
        # 1. Iniciar e Concluir Sessão
        data = {'materia': 'Cálculo I', 'metodo': 'POMODORO', 'disciplina': self.disciplina.id}
        sessao = TimerService.iniciar_nova_sessao(self.user, data)
        TimerService.finalizar(sessao)

        # 2. Verificar Atualização de Streak
        perfil = PerfilUsuario.objects.get(user=self.user)
        self.assertEqual(perfil.streak_atual, 1)

        # 3. Verificar Cultivo da Árvore
        self.assertTrue(ArvoreFoco.objects.filter(sessao=sessao).exists())

        # 4. Verificar Conquista Desbloqueada
        self.assertTrue(ConquistaUsuario.objects.filter(user=self.user, conquista__codigo='PRIMEIRO_PASSO').exists())

        # 5. Testar Idempotência (Garantir que reconcluir não duplica a árvore)
        GamificationService.processar_recompensas_sessao(sessao)
        self.assertEqual(ArvoreFoco.objects.filter(sessao=sessao).count(), 1)

    def test_sessao_cancelada_nao_gera_recompensas(self):
        data = {'materia': 'Álgebra Linear', 'metodo': 'POMODORO'}
        sessao = TimerService.iniciar_nova_sessao(self.user, data)
        TimerService.cancelar(sessao)

        self.assertFalse(ArvoreFoco.objects.filter(sessao=sessao).exists())
        perfil = PerfilUsuario.objects.get(user=self.user)
        self.assertEqual(perfil.streak_atual, 0)