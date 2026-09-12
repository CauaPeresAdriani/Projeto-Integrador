from django.urls import path, include
from . import views
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from accounts.views import (
    recuperacao_view,
    confirmar_recuperacao_senha_view,
)


## passando caminhos para as views e html correspondentes
urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.meu_login_view, name='login'),
    path('setup_2fa/', views.meu_setup_2fa_view, name='setup_2fa'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('verificar_2fa/', views.verificar_2fa_view, name='verificar_2fa'),
    path('logout/', views.meu_logout_view, name='logout'),
    path('home/', views.home_view, name='home'),
   path('recuperar-senha/', recuperacao_view, name='password_reset'),

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

path(
    'cadastro_participante/', views.cadastro_participante_view, name='cadastro_participante' ),
    

path(
    'upload_documento/',
    views.upload_documento_view,
    name='upload_documento'
),

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
    'participantes/<int:participante_id>/',
    views.detalhe_participante_view,
    name='detalhe_participante'
),

path(
    'participacoes/<int:participacao_id>/dados/novo/',
    views.cadastrar_dado_pesquisa_view,
    name='cadastrar_dado_pesquisa'
),

path(
    'documentos/<int:documento_id>/download/',
    views.download_documento_view,
    name='download_documento'
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
]