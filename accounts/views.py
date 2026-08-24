import base64
from io import BytesIO
import re
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
import qrcode
from django_otp.plugins.otp_totp.models import TOTPDevice
from accounts.models import Usuario

def meu_login_view(request):
## Instanciando variavel erro como none
    erro = None
## usa if method post para saber se o usuario clicou no botao de login
    if request.method == 'POST':
## Instanciando as variaveis de usuario e capturando os valores digitados pelo usuario no html      
        user_name = request.POST.get('username')
        senha = request.POST.get('password')
        usuario = authenticate(request, username=user_name, password=senha)
## se o usuario não é none
        if usuario is not None:
## armazena o id do usuario na sessao na hora do login antes de ser direcionado para 2fa            
            request.session['pre_otp_user_id'] = usuario.id
## verificando se o usuario ja escaneou o qr code em app auth
            dispositivo_confirmado = TOTPDevice.objects.filter(user=usuario, confirmed=True).first()
## se o qr code ou seja "dispositivo_confirmado" ja tiver sido escaneado / confirmado
            if dispositivo_confirmado:
# vai direto para a tela de digitar o PIN.
                return redirect('verificar_2fa')
# primeira vez dele (ou não tem dispositivo) precisa ver o qr code.
            else:
                return redirect('setup_2fa')
## mostrar erro caso nao tenha sido digitado usuario ou senha corretos
        else:
            erro = "Usuário ou senha incorretos."
## redireciona para a tela de login e mostra o erro caso tenha ocorrido algum erro
    return render(request, 'accounts/login.html', {'erro': erro})


def cadastro_view(request):
## Instanciando variavel erro como none
    erro = None
## se o metodo for post, ou seja, se o usuario clicou no botao de cadastro
    if request.method == 'POST':
## capturando os valores digitados pelo usuario no html
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        cpf = request.POST.get('cpf', '').strip()
        password = request.POST.get('password', '')
        perfil = request.POST.get('perfil', '').strip()
## verificando se todos os campos obrigatorios foram preenchidos     
        if not username or not email or not cpf or not password:
            erro = "Por favor, preencha todos os campos obrigatórios."
## verificando se o nome de usuario e valido       
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            erro = "O nome de usuário não pode ser um e-mail. Use apenas letras, números e underline (_), sem espaços."
## verificando se o username e valido
        elif Usuario.objects.filter(username=username).exists(): 
           erro = "Esse nome de usuário já está em uso. Escolha outro."
## verificando se o cpf e valido
        elif Usuario.objects.filter(cpf=cpf).exists():
            erro = "Este CPF já está cadastrado no sistema."
## se nao tiver erro
        if not erro:
## criando o usuario com os dados digitados pelo usuario no html 
            usuario = Usuario.objects.create_user(
                username=username,
                email=email,
                password=password,
                cpf=cpf,
                perfil=perfil
            )
            device = TOTPDevice.objects.get_or_create(user=Usuario.objects.get(username=username), name="Celular Principal", confirmed=False)
            return redirect('login')
            

        

    return render(request, 'accounts/cadastro.html' , {'erro': erro})



def meu_setup_2fa_view(request):
## pegando o id do usuario que esta tentando logar na sessao
    user_id = request.session.get('pre_otp_user_id')
## se nao tiver user_id o sistema manda para o login
    if not user_id:
        return redirect('login')  
## busca o usuario no banco
    usuario = Usuario.objects.get(id=user_id)
## cria ou pega o dispositivo TOTP do usuario
    device, created = TOTPDevice.objects.get_or_create(
        user=usuario, 
        name="Celular Principal", 
        defaults={'confirmed': False}
    )
## gerando a url do qr code para o app de autenticação
    otp_uri = device.config_url
## gerando o qr code a partir da url
    img = qrcode.make(otp_uri)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    imagem_qr_code = base64.b64encode(buffered.getvalue()).decode('utf-8')

    erro = None

## se o usuario clicou no botao de confirmar o qr code( token 6 digitos)
    if request.method == 'POST':
## aqui peguei o token digitado pelo usuario no html usando o name do input
        token_digitado = request.POST.get('token')
## verificando se o token digitado é valido
        if device.verify_token(token_digitado):
            device.confirmed = True
            device.save()
            
## logando direto pois o user_id ja foi validado e o token tbm
            login(request, usuario)
            if 'pre_otp_user_id' in request.session:
## deletando o user_id da sessao apos o login
                del request.session['pre_otp_user_id']
            return redirect('home') 
        else:
            erro = "Código inválido. Tente novamente."
            
    return render(request, 'accounts/setup_2fa.html', {'imagem_qr_code': imagem_qr_code, 'erro': erro})




## logica e a mesma so muda algumas coisa
def verificar_2fa_view(request):

    user_id = request.session.get('pre_otp_user_id')

    if not user_id:
        return redirect('login')
    usuario = Usuario.objects.get(id=user_id)
    device = TOTPDevice.objects.filter(user=usuario, confirmed=True).first()

    if not device:
        return redirect('setup_2fa')

    erro = None
  
    if request.method == 'POST':
        token_digitado = request.POST.get('token')

        if device.verify_token(token_digitado):

            login(request, usuario)
            if 'pre_otp_user_id' in request.session:
                del request.session['pre_otp_user_id']
                
            return redirect('home')  
        else:
            erro = "Código inválido. Tente novamente."

    return render(request, 'accounts/verificar_2fa.html', {'erro': erro})


## so pedindo o login para nao burlar a url
@login_required
def home_view(request):
    if request.user.is_authenticated:
        return render(request, 'accounts/home.html')

    return render(request, 'accounts/home.html')

## logout padrao q usei vindo do import q o django ja fornece
def meu_logout_view(request):
    logout(request) 
    return redirect('login') 