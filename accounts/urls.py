from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.meu_login_view, name='login'),
    path('setup_2fa/', views.meu_setup_2fa_view, name='setup_2fa'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('verificar_2fa/', views.verificar_2fa_view, name='verificar_2fa'),
    path('logout/', views.meu_logout_view, name='logout'),
    path('home/', views.home_view, name='home')
]