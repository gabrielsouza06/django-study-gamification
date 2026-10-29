from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum
from .models import SessaoEstudo, Disciplina, Avaliacao, MetaDeEstudo, PerfilUsuario, Conquista, ConquistaUsuario, ArvoreFoco
from .services import TimerService

# --- AUTENTICAÇÃO ---

def cadastro(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserCreationForm()
    return render(request, "estudos/cadastro.html", {"form": form})

# --- DASHBOARD PRINCIPAL ---

@login_required
def index(request):
    user = request.user
    perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
    
    sessoes = SessaoEstudo.objects.filter(user=user, estado='CONCLUIDO').order_by("-data")
    sessao_ativa = SessaoEstudo.objects.filter(user=user, estado__in=['EM_ANDAMENTO', 'PAUSADO', 'EM_DESCANSO']).first()

    total_minutos = sessoes.aggregate(Sum('duracao_minutos'))['duracao_minutos__sum'] or 0
    horas = total_minutos // 60
    minutos_restantes = total_minutos % 60

    disciplinas = Disciplina.objects.filter(user=user, ativa=True)
    metas = MetaDeEstudo.objects.filter(user=user, ativa=True)
    avaliacoes = Avaliacao.objects.filter(user=user, status__in=['PENDENTE', 'EM_ANDAMENTO']).order_by('data_vencimento')[:5]
    floresta = ArvoreFoco.objects.filter(user=user).order_by('-plantada_em')[:12]
    conquistas_desbloqueadas = ConquistaUsuario.objects.filter(user=user).select_related('conquista')

    context = {
        "perfil": perfil,
        "sessoes": sessoes[:5],
        "sessao_ativa": sessao_ativa,
        "horas": horas,
        "minutos_restantes": minutos_restantes,
        "disciplinas": disciplinas,
        "metas": metas,
        "avaliacoes": avaliacoes,
        "floresta": floresta,
        "conquistas_desbloqueadas": conquistas_desbloqueadas,
    }
    return render(request, "estudos/index.html", context)

# --- TIMER E SESSÕES ---

@login_required
def iniciar_sessao(request):
    if request.method == "POST":
        SessaoEstudo.objects.filter(user=request.user, estado__in=['EM_ANDAMENTO', 'PAUSADO', 'EM_DESCANSO']).update(estado='CANCELADO')
        sessao = TimerService.iniciar_nova_sessao(request.user, request.POST)
        return redirect('timer', pk=sessao.id)
    return redirect('home')

@login_required
def pagina_timer(request, pk):
    sessao = get_object_or_404(SessaoEstudo, pk=pk, user=request.user)
    if sessao.estado in ['CONCLUIDO', 'CANCELADO']:
        return redirect('home')
    sessao = TimerService.sincronizar_estado(sessao)
    return render(request, "estudos/timer.html", {"sessao": sessao})

# --- ENDPOINTS AJAX DE CONTROLE DO TIMER ---

@login_required
def api_estado_timer(request, pk):
    sessao = get_object_or_404(SessaoEstudo, pk=pk, user=request.user)
    sessao = TimerService.sincronizar_estado(sessao)
    return JsonResponse({
        "id": sessao.id,
        "materia": sessao.materia,
        "estado": sessao.estado,
        "etapa_atual": sessao.get_etapa_atual_display(),
        "etapa_code": sessao.etapa_atual,
        "tempo_restante_segundos": sessao.tempo_restante_segundos,
        "ciclos_concluidos": sessao.ciclos_concluidos,
        "total_ciclos": sessao.total_ciclos_planejados,
    })

@login_required
@require_POST
def api_pausar(request, pk):
    sessao = get_object_or_404(SessaoEstudo, pk=pk, user=request.user)
    TimerService.pausar(sessao)
    return JsonResponse({"status": "ok"})

@login_required
@require_POST
def api_retomar(request, pk):
    sessao = get_object_or_404(SessaoEstudo, pk=pk, user=request.user)
    TimerService.retomar(sessao)
    return JsonResponse({"status": "ok"})

@login_required
@require_POST
def api_avancar(request, pk):
    sessao = get_object_or_404(SessaoEstudo, pk=pk, user=request.user)
    TimerService.avancar_etapa(sessao)
    return JsonResponse({"status": "ok"})

@login_required
@require_POST
def api_finalizar(request, pk):
    sessao = get_object_or_404(SessaoEstudo, pk=pk, user=request.user)
    TimerService.finalizar(sessao, antecipado=True)
    return JsonResponse({"status": "ok"})

@login_required
@require_POST
def api_cancelar(request, pk):
    sessao = get_object_or_404(SessaoEstudo, pk=pk, user=request.user)
    TimerService.cancelar(sessao)
    return JsonResponse({"status": "ok"})

@login_required
def editar(request, pk):
    sessao = get_object_or_404(SessaoEstudo, pk=pk, user=request.user)
    if request.method == "POST":
        sessao.materia = request.POST.get("materia")
        sessao.duracao_minutos = request.POST.get("duracao_minutos")
        sessao.save()
        return redirect("home")
    return render(request, "estudos/editar.html", {"sessao": sessao})

@login_required
def deletar(request, pk):
    sessao = get_object_or_404(SessaoEstudo, pk=pk, user=request.user)
    sessao.delete()
    return redirect("home")

# --- MÓDULO ACADÊMICO E GAMIFICAÇÃO ---

@login_required
def lista_disciplinas(request):
    disciplinas = Disciplina.objects.filter(user=request.user, ativa=True)
    return render(request, "estudos/disciplinas.html", {"disciplinas": disciplinas})

@login_required
def criar_disciplina(request):
    if request.method == "POST":
        Disciplina.objects.create(
            user=request.user,
            nome=request.POST.get("nome"),
            descricao=request.POST.get("descricao"),
            cor_hex=request.POST.get("cor_hex", "#4f46e5")
        )
    return redirect("lista_disciplinas")

@login_required
def deletar_disciplina(request, pk):
    disciplina = get_object_or_404(Disciplina, pk=pk, user=request.user)
    disciplina.delete()
    return redirect("lista_disciplinas")

@login_required
def lista_avaliacoes(request):
    avaliacoes = Avaliacao.objects.filter(user=request.user).order_by("data_vencimento")
    disciplinas = Disciplina.objects.filter(user=request.user, ativa=True)
    return render(request, "estudos/avaliacoes.html", {"avaliacoes": avaliacoes, "disciplinas": disciplinas})

@login_required
def criar_avaliacao(request):
    if request.method == "POST":
        disciplina = get_object_or_404(Disciplina, pk=request.POST.get("disciplina"), user=request.user)
        Avaliacao.objects.create(
            user=request.user,
            disciplina=disciplina,
            titulo=request.POST.get("titulo"),
            tipo=request.POST.get("tipo"),
            data_vencimento=request.POST.get("data_vencimento"),
            meta_horas_preparacao=request.POST.get("meta_horas_preparacao", 5)
        )
    return redirect("lista_avaliacoes")

@login_required
def galeria_conquistas(request):
    conquistas = Conquista.objects.all()
    desbloqueadas = {c.conquista_id: c.desbloqueada_em for c in ConquistaUsuario.objects.filter(user=request.user)}
    
    conquistas_todas = []
    for c in conquistas:
        conquistas_todas.append({
            "conquista": c,
            "desbloqueada": c.id in desbloqueadas,
            "desbloqueada_em": desbloqueadas.get(c.id)
        })
    return render(request, "estudos/conquistas.html", {"conquistas_todas": conquistas_todas})