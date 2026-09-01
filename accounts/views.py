import base64
from io import BytesIO
import re
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
import qrcode
from django_otp.plugins.otp_totp.models import TOTPDevice
from accounts.models import Usuario, AuditLog
from datetime import timedelta 
from django.utils import timezone
import time
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.db.models import Q
import os



def meu_login_view(request):
    ## Instanciando variavel erro como none
    erro = None
    ## usa if method post para saber se o usuario clicou no botao de login
    if request.method == 'POST':
        ## Instanciando as variaveis de usuario e capturando os valores digitados pelo usuario no html      
        user_name = request.POST.get('username')
        senha = request.POST.get('password')
         # Procura o usuário no banco
        usuario_cadastrado = Usuario.objects.filter(
            username=user_name
        ).first()
        # Verifica se o usuário está bloqueado
        if usuario_cadastrado:
            agora = timezone.now()
            if (
                usuario_cadastrado.bloqueado_ate
                and usuario_cadastrado.bloqueado_ate > agora
            ):
                erro = "Conta temporariamente bloqueada. Tente novamente mais tarde."

                 # Registra tentativa durante o bloqueio.
                AuditLog.objects.create(
                    usuario=usuario_cadastrado,
                    evento='Tentativa durante bloqueio',
                    ip=request.META.get('REMOTE_ADDR'),
                    resultado='Bloqueado',
                    detalhes='Tentativa de login realizada enquanto a conta estava bloqueada.'
                 )

                return render(
                    request,
                    'accounts/login.html',
                    {'erro': erro}
                )
            # Libera a conta após o fim do bloqueio
            if (
                usuario_cadastrado.bloqueado_ate
                and usuario_cadastrado.bloqueado_ate <= agora
            ):
                usuario_cadastrado.bloqueado_ate = None
                usuario_cadastrado.tentativas_login = 0
                usuario_cadastrado.save()
                # Verifica usuário e senha
        usuario = authenticate(
            request,
            username=user_name,
            password=senha
        )
        # Login correto
        if usuario is not None:
            # Zera as tentativas
            usuario.tentativas_login = 0
            usuario.bloqueado_ate = None
            usuario.save()
            # O usuário acertou o usuário e a senha,
            # mas ainda NÃO concluiu o login porque falta validar o 2FA.
            AuditLog.objects.create(
            usuario=usuario,
            evento="Senha validada",
            ip=request.META.get('REMOTE_ADDR'),
            resultado="Sucesso",
            detalhes="Usuário e senha validados. Aguardando validação do segundo fator (2FA)."
            )
        # Guarda o usuário na sessão para o 2FA
            request.session['pre_otp_user_id'] = usuario.id
            # Verifica se o 2FA já foi configurado
            dispositivo_confirmado = TOTPDevice.objects.filter(
                user=usuario,
                confirmed=True
            ).first()

            if dispositivo_confirmado:

                return redirect('verificar_2fa')
            
            else:
                return redirect('setup_2fa')
        # Usuário ou senha incorretos
        else:
            if usuario_cadastrado:
                # Aumenta o número de tentativas
                usuario_cadastrado.tentativas_login += 1
                AuditLog.objects.create(
                    usuario=usuario_cadastrado,
                    evento='Login',
                    ip=request.META.get('REMOTE_ADDR'),
                    resultado='Falha',
                    detalhes=f'Tentativa de login incorreta. Tentativa {usuario_cadastrado.tentativas_login}.'
                )
                # Cria um atraso conforme o número de tentativas.
                atraso = usuario_cadastrado.tentativas_login
                # Aplica o atraso antes de permitir uma nova tentativa.
                time.sleep(atraso)
                # Bloqueia após 5 tentativas
                if usuario_cadastrado.tentativas_login >= 5:
                    usuario_cadastrado.bloqueado_ate = (
                        timezone.now() + timedelta(minutes=5)
                    )
                    usuario_cadastrado.tentativas_login = 5
                    erro = "Muitas tentativas. Conta bloqueada por 5 minutos."
                    # Registra o bloqueio da conta.
                    AuditLog.objects.create(
                        usuario=usuario_cadastrado,
                        evento='Bloqueio de conta',
                        ip=request.META.get('REMOTE_ADDR'),
                        resultado='Bloqueado',
                        detalhes='Conta bloqueada após 5 tentativas de login incorretas.'
                    )
                else:
                    restantes = 5 - usuario_cadastrado.tentativas_login
                    erro = (
                        f"Usuário ou senha incorretos. "
                        f"Restam {restantes} tentativa(s)."
                    )
                usuario_cadastrado.save()
            else:
                erro = "Usuário ou senha incorretos."
    # Mostra a tela de login
    return render(
        request,
        'accounts/login.html',
        {'erro': erro}
    )
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
            return render(request, 'accounts/cadastro.html', {'erro': erro})
## verificando se o nome de usuario e valido       
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            erro = "O nome de usuário não pode ser um e-mail. Use apenas letras, números e underline (_), sem espaços."
            return render(request, 'accounts/cadastro.html', {'erro': erro})
## verificando se o username e valido
        elif Usuario.objects.filter(username=username).exists(): 
           erro = "Esse nome de usuário já está em uso. Escolha outro."
           return render(request, 'accounts/cadastro.html', {'erro': erro})
## verificando se o cpf e valido
        elif Usuario.objects.filter(cpf=cpf).exists():
            erro = "Este CPF já está cadastrado no sistema."
            return render(request, 'accounts/cadastro.html', {'erro': erro})
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
            device, created = TOTPDevice.objects.get_or_create(
            user=usuario,
            name="Celular Principal",
            defaults={
            'confirmed': False
            }
            )
            return redirect('login')
        
    return render(request, 'accounts/cadastro.html', {'erro': erro})


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




def verificar_2fa_view(request):

    # Pega o ID do usuário que está fazendo login.
    user_id = request.session.get('pre_otp_user_id')

    # Se não existir usuário na sessão, volta para o login.
    if not user_id:
        return redirect('login')

    # Busca o usuário no banco.
    usuario = Usuario.objects.get(id=user_id)

    # Verifica se o 2FA está temporariamente bloqueado.
    if (
        usuario.bloqueado_2fa_ate
        and usuario.bloqueado_2fa_ate > timezone.now()
    ):
        erro = "2FA temporariamente bloqueado. Tente novamente mais tarde."

        return render(
            request,
            'accounts/verificar_2fa.html',
            {'erro': erro}
        )

    # Libera o 2FA quando o bloqueio termina.
    if (
        usuario.bloqueado_2fa_ate
        and usuario.bloqueado_2fa_ate <= timezone.now()
    ):
        usuario.bloqueado_2fa_ate = None
        usuario.tentativas_2fa = 0
        usuario.save()
        # Registra o 2FA correto.
        AuditLog.objects.create(
            usuario=usuario,
            evento="2FA desbloqueado",
            ip=request.META.get('REMOTE_ADDR'),
            resultado="Sucesso",
            detalhes="Código 2FA validado corretament."
        )
    # Procura o dispositivo 2FA confirmado.
    device = TOTPDevice.objects.filter(
        user=usuario,
        confirmed=True
    ).first()

    # Se não existir dispositivo, vai para configuração.
    if not device:
        return redirect('setup_2fa')

    erro = None

    # Verifica se o formulário foi enviado.
    if request.method == 'POST':

        # Pega o código digitado.
        token_digitado = request.POST.get('token')

        # Verifica o código 2FA.
        if device.verify_token(token_digitado):

            # Login concluído.
            login(request, usuario)

             # Registra no histórico que o login foi realmente concluído.
            AuditLog.objects.create(
            usuario=usuario,
            evento="Login bem-sucedido",
            ip=request.META.get('REMOTE_ADDR'),
            resultado="Sucesso",
            detalhes="Login concluído após validação do usuário, senha e segundo fator (2FA)."
            )

            # Zera as tentativas do 2FA.
            usuario.tentativas_2fa = 0
            usuario.bloqueado_2fa_ate = None
            usuario.save()

            # Remove o usuário temporário da sessão.
            if 'pre_otp_user_id' in request.session:
                del request.session['pre_otp_user_id']

            return redirect('home')

        else:

            # Aumenta o número de tentativas.
            usuario.tentativas_2fa += 1
            # Registra a tentativa de 2FA incorreta.
            AuditLog.objects.create(
                usuario=usuario,
                evento='2FA',
                ip=request.META.get('REMOTE_ADDR'),
                resultado='Falha',
                detalhes=f'Código 2FA incorreto. Tentativa {usuario.tentativas_2fa}.'
            )

            # Cria atraso progressivo.
            atraso = usuario.tentativas_2fa
            time.sleep(atraso)

            # Bloqueia após 5 tentativas.
            if usuario.tentativas_2fa >= 5:

                usuario.bloqueado_2fa_ate = (
                    timezone.now() + timedelta(minutes=5)
                )

                usuario.tentativas_2fa = 5

                erro = "Muitas tentativas. 2FA bloqueado por 5 minutos."

                # Registra o bloqueio do 2FA.
                AuditLog.objects.create(
                usuario=usuario,
                evento='Bloqueio 2FA',
                ip=request.META.get('REMOTE_ADDR'),
                resultado='Bloqueado',
                detalhes='2FA bloqueado após 5 tentativas incorretas.'
                )

            else:

                restantes = 5 - usuario.tentativas_2fa

                erro = (
                    f"Código inválido. "
                    f"Restam {restantes} tentativa(s)."
                )

            # Salva as alterações.
            usuario.save()

    return render(
        request,
        'accounts/verificar_2fa.html',
        {'erro': erro}
    )

# Exige que o usuário esteja logado para acessar a página inicial.
@login_required
def home_view(request):
    # Exibe a página inicial.
    return render(request, 'accounts/home.html')

# Faz o logout do usuário.
def meu_logout_view(request):

    # Encerra a sessão.
    logout(request)

    # Volta para a tela de login.
    return redirect('login')


def recuperacao_view(request):
    erro = None
    if request.method == 'POST':
        # Captura o valor que pode ser tanto username quanto email
        identificador = request.POST.get('identificador', '').strip()
        
        if not identificador:
            return render(request, 'accounts/recuperacao.html', {'erro': 'Preencha o campo.'})

        # Requisito 2.1: Busca o usuário usando Q (Email OU Username)
        usuario = Usuario.objects.filter(
            Q(email=identificador) | Q(username=identificador)
        ).first()

        if usuario:
            # Requisito 2.2: Gera o token criptográfico
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            token = default_token_generator.make_token(usuario)

            # Monta o link absoluto que irá no corpo do e-mail
            link = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )

            # Envia o e-mail real
            send_mail(
                subject='ClinSecure - Recuperação de Senha',
                message=f'Olá, {usuario.username}.\n\nVocê solicitou a redefinição de senha. Clique no link abaixo para criar uma nova credencial:\n{link}\n\nSe não foi você, ignore este e-mail.',
                from_email=os.getenv('EMAIL_HOST_USER'),
                recipient_list=[usuario.email],
                fail_silently=False,
            )

        # Redireciona sempre para a mesma tela de sucesso (evita enumeração de usuários)
        return redirect('password_reset_done')

    return render(request, 'accounts/recuperacao.html', {'erro': erro})