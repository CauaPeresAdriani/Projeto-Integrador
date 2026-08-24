from django.shortcuts import redirect, render
# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login  
from accounts.models import Usuario
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.http import HttpResponse


def home(request):
    return HttpResponse("Projeto Integrador funcionando!")


def meu_login_view(request):
    erro = None
    if request.method == 'POST':
        user_name = request.POST.get('username')
        senha = request.POST.get('password')
        usuario = authenticate(request, username=user_name, password=senha)
        
        if usuario is not None:
            device = TOTPDevice.objects.filter(user=usuario, confirmed=True).first()
            if not device:
                login(request, usuario)
                return redirect('setup_2fa')
            else:
                request.session['pre_otp_user_id'] = usuario.id
                return redirect('verificar_2fa')
        else:
            erro = "Usuário ou senha incorretos."

    return render(request, 'accounts/login.html', {'erro': erro})

def cadastro_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        cpf = request.POST.get('cpf')
        perfil = request.POST.get('perfil')


        
        usuario = Usuario.objects.create_user(
            username=username,
            email=email,
            password=password,
            cpf=cpf,
            perfil=perfil
        )

        device = TOTPDevice.objects.get_or_create(user=Usuario.objects.get(username=username), name="Celular Principal", confirmed=False)

        return redirect('login')

    return render(request, 'accounts/cadastro.html')



def meu_setup_2fa_view(request):

    user_id = request.session.get('pre_otp_user_id')
    if user_id:
        usuario = Usuario.objects.get(id=user_id)
    else:
        usuario = request.user
        

    device, created = TOTPDevice.objects.get_or_create(
        user=usuario, 
        name="Celular Principal", 
        defaults={'confirmed': False}
    )
    
    erro = None
    if request.method == 'POST':
        token_digitado = request.POST.get('token')

        if device.verify_token(token_digitado):
            device.confirmed = True
            device.save()
            

            if user_id:
                login(request, usuario)
                del request.session['pre_otp_user_id']
                
            return redirect('home') 
        else:
            erro = "Código inválido. Tente novamente."
            
    url_qrcode = device.config_url 
    return render(request, 'accounts/setup_2fa.html', {'url_qrcode': url_qrcode, 'erro': erro})