from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Rotas de Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='estudos/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('cadastro/', views.cadastro, name='cadastro'),

    # Demais rotas existentes...
    path('', views.index, name='home'),
    path('iniciar/', views.iniciar_sessao, name='iniciar_sessao'),
    path('timer/<int:pk>/', views.pagina_timer, name='timer'),
    path('api/timer/<int:pk>/estado/', views.api_estado_timer, name='api_estado_timer'),
    path('api/timer/<int:pk>/pausar/', views.api_pausar, name='api_pausar'),
    path('api/timer/<int:pk>/retomar/', views.api_retomar, name='api_retomar'),
    path('api/timer/<int:pk>/avancar/', views.api_avancar, name='api_avancar'),
    path('api/timer/<int:pk>/finalizar/', views.api_finalizar, name='api_finalizar'),
    path('api/timer/<int:pk>/cancelar/', views.api_cancelar, name='api_cancelar'),
    path('editar/<int:pk>/', views.editar, name='editar'),
    path('deletar/<int:pk>/', views.deletar, name='deletar'),
    path('disciplinas/', views.lista_disciplinas, name='lista_disciplinas'),
    path('disciplinas/criar/', views.criar_disciplina, name='criar_disciplina'),
    path('disciplinas/deletar/<int:pk>/', views.deletar_disciplina, name='deletar_disciplina'),
    path('avaliacoes/', views.lista_avaliacoes, name='lista_avaliacoes'),
    path('avaliacoes/criar/', views.criar_avaliacao, name='criar_avaliacao'),
    path('conquistas/', views.galeria_conquistas, name='galeria_conquistas'),
]