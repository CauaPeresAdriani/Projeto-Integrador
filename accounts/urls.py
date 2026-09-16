from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from accounts.views import (
    recuperacao_view,
    confirmar_recuperacao_senha_view,
)


# Passando os caminhos para as views e HTML correspondentes
urlpatterns = [

    # Autenticação
    path('', views.home_view, name='home'),
    path('home/', views.home_view, name='home'),
    path('login/', views.meu_login_view, name='login'),
    path('setup_2fa/', views.meu_setup_2fa_view, name='setup_2fa'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('verificar_2fa/', views.verificar_2fa_view, name='verificar_2fa'),
    path('logout/', views.meu_logout_view, name='logout'),

    # Recuperação de senha
    path(
        'recuperar-senha/',
        recuperacao_view,
        name='password_reset'
    ),

    path(
        'recuperar-senha/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    path(
        'recuperar-senha/<uidb64>/<token>/',
        confirmar_recuperacao_senha_view,
        name='password_reset_confirm'
    ),

    path(
        'recuperar-senha/concluido/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),

    # Cadastro de participante
    path(
        'cadastro_participante/',
        views.cadastro_participante_view,
        name='cadastro_participante'
    ),

    # Documentos
    path(
        'upload_documento/',
        views.upload_documento_view,
        name='upload_documento'
    ),

    path(
        'documentos/<int:documento_id>/download/',
        views.download_documento_view,
        name='download_documento'
    ),

    path(
        'documentos/<int:documento_id>/visualizar/',
        views.visualizar_documento_view,
        name='visualizar_documento'
    ),

    path(
        'documentos/<int:documento_id>/acesso/',
        views.conceder_acesso_documento_view,
        name='conceder_acesso_documento'
    ),

    path(
        'acessos/<int:acesso_id>/revogar/',
        views.revogar_acesso_documento_view,
        name='revogar_acesso_documento'
    ),

    # Pesquisas
    path(
        'pesquisas/',
        views.lista_pesquisas_view,
        name='lista_pesquisas'
    ),

    path(
        'pesquisas/<int:pesquisa_id>/',
        views.detalhe_pesquisa_view,
        name='detalhe_pesquisa'
    ),

    path(
    'pesquisas/<int:pesquisa_id>/editar/',
    views.editar_pesquisa_view,
    name='editar_pesquisa'
),

    # Participantes
    path(
        'participantes/<int:participante_id>/',
        views.detalhe_participante_view,
        name='detalhe_participante'
    ),

    path(
        'ativar-participante/<uidb64>/<token>/',
        views.ativar_participante_view,
        name='ativar_participante'
    ),

    # Dados da pesquisa
    path(
        'participacoes/<int:participacao_id>/dados/novo/',
        views.cadastrar_dado_pesquisa_view,
        name='cadastrar_dado_pesquisa'
    ),

    # LGPD - Meus dados
    path(
        'meus-dados/',
        views.meus_dados_view,
        name='meus_dados'
    ),

    path(
        'meus-dados/consentir/',
        views.consentir_dados_view,
        name='consentir_dados'
    ),

    path(
        'meus-dados/consentimento/<int:consentimento_id>/revogar/',
        views.revogar_consentimento_view,
        name='revogar_consentimento'
    ),

    path(
        'meus-dados/exportar/',
        views.exportar_dados_view,
        name='exportar_dados'
    ),

    path(
        'meus-dados/excluir/',
        views.excluir_dados_view,
        name='excluir_dados'
    ),

    # Análise dos logs de auditoria
    path(
        'logs/analise/',
        views.analise_logs_view,
        name='analise_logs'
    ),
]