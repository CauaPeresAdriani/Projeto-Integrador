from django.urls import path, include
from . import views
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from accounts.views import recuperacao_view, confirmar_recuperacao_senha_view  


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
]