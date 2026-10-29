from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Disciplina(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disciplinas', null=True, blank=True)
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    cor_hex = models.CharField(max_length=7, default='#4f46e5')
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

class Avaliacao(models.Model):
    TIPO_CHOICES = [
        ('PROVA', 'Prova'),
        ('TRABALHO', 'Trabalho'),
        ('EXERCICIO', 'Lista de Exercícios'),
        ('OUTRO', 'Outro'),
    ]
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDA', 'Concluída'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avaliacoes', null=True, blank=True)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name='avaliacoes')
    titulo = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='PROVA')
    data_vencimento = models.DateField()
    meta_horas_preparacao = models.PositiveIntegerField(default=5)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    descricao = models.TextField(blank=True, null=True)

    def total_minutos_estudados(self):
        minutos = self.sessoes.filter(estado='CONCLUIDO').aggregate(models.Sum('duracao_minutos'))['duracao_minutos__sum']
        return minutos or 0

    def progresso_percentual(self):
        meta_minutos = self.meta_horas_preparacao * 60
        if meta_minutos == 0:
            return 100.0
        pct = (self.total_minutos_estudados() / meta_minutos) * 100
        return min(100.0, round(pct, 1))

    def __str__(self):
        return f"{self.titulo} - {self.disciplina.nome}"

class MetaDeEstudo(models.Model):
    PERIODO_CHOICES = [
        ('SEMANAL', 'Semanal'),
        ('MENSAL', 'Mensal'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='metas', null=True, blank=True)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name='metas')
    periodo = models.CharField(max_length=10, choices=PERIODO_CHOICES, default='SEMANAL')
    horas_alvo = models.PositiveIntegerField()
    data_inicio = models.DateField()
    data_fim = models.DateField()
    ativa = models.BooleanField(default=True)

    def total_minutos_realizados(self):
        minutos = SessaoEstudo.objects.filter(
            user=self.user,
            disciplina=self.disciplina,
            estado='CONCLUIDO',
            data__date__gte=self.data_inicio,
            data__date__lte=self.data_fim
        ).aggregate(models.Sum('duracao_minutos'))['duracao_minutos__sum']
        return minutos or 0

    def progresso_percentual(self):
        alvo_minutos = self.horas_alvo * 60
        if alvo_minutos == 0:
            return 100.0
        return min(100.0, round((self.total_minutos_realizados() / alvo_minutos) * 100, 1))

class SessaoEstudo(models.Model):
    METODO_CHOICES = [
        ('POMODORO', 'Pomodoro (25/5)'),
        ('CONTINUO', 'Estudo Contínuo'),
        ('CINQUENTA_DEZ', 'Método 50/10'),
        ('PERSONALIZADO', 'Personalizado'),
    ]
    ESTADO_CHOICES = [
        ('CONFIGURANDO', 'Configurando'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('EM_DESCANSO', 'Em Descanso'),
        ('PAUSADO', 'Pausado'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]
    ETAPA_CHOICES = [
        ('FOCO', 'Foco'),
        ('DESCANSO_CURTO', 'Descanso Curto'),
        ('DESCANSO_LONGO', 'Descanso Longo'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessoes', null=True, blank=True)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessoes')
    avaliacao = models.ForeignKey(Avaliacao, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessoes')
    materia = models.CharField(max_length=100)
    assunto = models.CharField(max_length=150, blank=True, null=True)
    duracao_minutos = models.PositiveIntegerField(default=0)
    data = models.DateTimeField(default=timezone.now)

    metodo = models.CharField(max_length=20, choices=METODO_CHOICES, default='POMODORO')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='CONCLUIDO')
    etapa_atual = models.CharField(max_length=20, choices=ETAPA_CHOICES, default='FOCO')
    
    tempo_foco_min = models.PositiveIntegerField(default=25)
    tempo_descanso_curto_min = models.PositiveIntegerField(default=5)
    tempo_descanso_longo_min = models.PositiveIntegerField(default=15)
    total_ciclos_planejados = models.PositiveIntegerField(default=4)
    ciclos_concluidos = models.PositiveIntegerField(default=0)

    horario_inicio = models.DateTimeField(blank=True, null=True)
    horario_termino_previsto = models.DateTimeField(blank=True, null=True)
    tempo_restante_segundos = models.PositiveIntegerField(default=0)
    segundos_foco_acumulados = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.materia} - {self.duracao_minutos} min"

class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    streak_atual = models.PositiveIntegerField(default=0)
    maior_streak = models.PositiveIntegerField(default=0)
    ultimo_dia_estudado = models.DateField(null=True, blank=True)

class Conquista(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    icone = models.CharField(max_length=50, default='bi-award-fill')
    criterio = models.CharField(max_length=150)

    def __str__(self):
        return self.nome

class ConquistaUsuario(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conquistas')
    conquista = models.ForeignKey(Conquista, on_delete=models.CASCADE)
    desbloqueada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'conquista')

class ArvoreFoco(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='floresta')
    sessao = models.OneToOneField(SessaoEstudo, on_delete=models.CASCADE, related_name='arvore')
    tipo_arvore = models.CharField(max_length=50, default='Carvalho Vigoroso')
    icone_css = models.CharField(max_length=50, default='bi-tree-fill')
    plantada_em = models.DateTimeField(auto_now_add=True)