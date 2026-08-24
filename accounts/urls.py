from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.meu_login_view, name='login'),
    path('setup_2fa/', views.meu_setup_2fa_view, name='setup_2fa'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
]