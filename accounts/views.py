import base64
import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta
from io import BytesIO
import qrcode
import requests

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db.models import Q, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from django_otp.plugins.otp_totp.models import TOTPDevice

from .crypto import (
    decrypt_data,
    decrypt_file,
    encrypt_data,
    encrypt_file,
)

from .models import (
    Acesso,
    AuditLog,
    Consentimento,
    DadoPesquisa,
    Documento,
    ParticipacaoPesquisa,
    Participante,
    Pesquisa,
    Usuario,
)

from .permissions import (
    eh_admin_ou_coordenador,
    usuario_pode_acessar_documento,
    usuario_pode_acessar_participante,
    usuario_pode_acessar_pesquisa,
)

MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB
## LOGICA DE LOGIN ##

def meu_login_view(request):

    erro = None

    if request.method == 'POST':

        # E-mail ou usuário informado no formulário
        user_name = request.POST.get('username', '').strip()
        senha = request.POST.get('password', '')

        # Primeiro tenta localizar pelo e-mail.
        # Isso permite que participantes entrem usando o e-mail.
        usuario_cadastrado = Usuario.objects.filter(
            email__iexact=user_name
        ).first()

        # Mantém compatibilidade com contas antigas que ainda usam username.
        if usuario_cadastrado:
            username_login = usuario_cadastrado.username
        else:
            usuario_cadastrado = Usuario.objects.filter(
                username=user_name
            ).first()

            username_login = user_name

        # Verifica se o usuário está bloqueado
        if usuario_cadastrado:

            agora = timezone.now()

            if (
                usuario_cadastrado.bloqueado_ate
                and usuario_cadastrado.bloqueado_ate > agora
            ):

                erro = (
                    "Conta temporariamente bloqueada. "
                    "Tente novamente mais tarde."
                )

                AuditLog.objects.create(
                    usuario=usuario_cadastrado,
                    evento='Tentativa durante bloqueio',
                    ip=request.META.get('REMOTE_ADDR'),
                    resultado='Bloqueado',
                    detalhes=(
                        'Tentativa de login realizada enquanto '
                        'a conta estava bloqueada.'
                    )
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
            username=username_login,
            password=senha
        )

        # Login correto
        if usuario is not None:

            # Zera as tentativas
            usuario.tentativas_login = 0
            usuario.bloqueado_ate = None
            usuario.save()

            AuditLog.objects.create(
                usuario=usuario,
                evento="Senha validada",
                ip=request.META.get('REMOTE_ADDR'),
                resultado="Sucesso",
                detalhes=(
                    "Usuário e senha validados. "
                    "Aguardando validação do segundo fator (2FA)."
                )
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
                    detalhes=(
                        'Tentativa de login incorreta. '
                        f'Tentativa {usuario_cadastrado.tentativas_login}.'
                    )
                )

                # Cria um atraso conforme o número de tentativas
                atraso = usuario_cadastrado.tentativas_login

                time.sleep(atraso)

                # Bloqueia após 5 tentativas
                if usuario_cadastrado.tentativas_login >= 5:

                    usuario_cadastrado.bloqueado_ate = (
                        timezone.now() + timedelta(minutes=5)
                    )

                    usuario_cadastrado.tentativas_login = 5

                    erro = (
                        "Muitas tentativas. "
                        "Conta bloqueada por 5 minutos."
                    )

                    AuditLog.objects.create(
                        usuario=usuario_cadastrado,
                        evento='Bloqueio de conta',
                        ip=request.META.get('REMOTE_ADDR'),
                        resultado='Bloqueado',
                        detalhes=(
                            'Conta bloqueada após 5 tentativas '
                            'de login incorretas.'
                        )
                    )

                else:

                    restantes = (
                        5 - usuario_cadastrado.tentativas_login
                    )

                    erro = (
                        "Usuário ou senha incorretos. "
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

## LOGICA DE CADASTRO ##

@login_required
def cadastro_view(request):

    if request.user.perfil not in ['administrador', 'coordenador']:
        return redirect('home')
    ## Instanciando variavel erro como none
    erro = None
    ## se o metodo for post, ou seja, se o usuario clicou no botao de cadastro
    if request.method == 'POST':
    ## capturando os valores digitados pelo usuario no html
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        perfil = request.POST.get('perfil', '').strip()
        perfis_permitidos = {
            'administrador': ['responsavel', 'pesquisador', 'coordenador'],
            'coordenador': ['responsavel', 'pesquisador'],
        }

        if perfil not in perfis_permitidos.get(request.user.perfil, []):
            erro = "Você não tem permissão para cadastrar esse perfil."
            return render(request, 'accounts/cadastro.html', {'erro': erro})
    ## verificando se todos os campos obrigatorios foram preenchidos     
        if not username or not email or not password:
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
    ## se nao tiver erro
        if not erro:
    ## criando o usuario com os dados digitados pelo usuario no html 
            usuario = Usuario.objects.create_user(
                username=username,
                email=email,
                password=password,
                perfil=perfil
            )
            ## criando dispositivo para 2fa e setando como nao confirmado
            device, created = TOTPDevice.objects.get_or_create(
            user=usuario,
            name="Celular Principal",
            defaults={
            'confirmed': False
            }
            )
            return redirect('login')
        
    return render(request, 'accounts/cadastro.html', {'erro': erro})

@login_required
def cadastro_participante_view(request):

    if request.user.perfil != "responsavel":
        return HttpResponse(
            "Acesso negado. Apenas usuários com perfil 'responsável' podem cadastrar participantes.",
            status=403
        )

    pesquisas = Pesquisa.objects.filter(
        responsavel=request.user
    )

    erro = None

    if request.method == 'POST':

        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        data_nascimento = request.POST.get(
            'data_nascimento',
            ''
        ).strip()
        cpf = request.POST.get('cpf', '').strip()
        pesquisa_id = request.POST.get('pesquisa')

        # Normalização
        cpf = normalizar_cpf(cpf)

        # Campos obrigatórios
        if not nome or not email or not data_nascimento or not cpf or not pesquisa_id:

            erro = "Preencha todos os campos obrigatórios."

            return render(
                request,
                'accounts/cadastro_participante.html',
                {
                    'erro': erro,
                    'pesquisas': pesquisas
                }
            )

        # Validação do e-mail
        try:
            validate_email(email)
        except ValidationError:

            erro = "Informe um endereço de e-mail válido."

            return render(
                request,
                'accounts/cadastro_participante.html',
                {
                    'erro': erro,
                    'pesquisas': pesquisas
                }
            )

        # Validação do CPF
        if len(cpf) != 11 or not cpf.isdigit():

            erro = "Informe um CPF válido com 11 dígitos."

            return render(
                request,
                'accounts/cadastro_participante.html',
                {
                    'erro': erro,
                    'pesquisas': pesquisas
                }
            )

        # Validação matemática do CPF
        def cpf_valido(cpf):

            if cpf == cpf[0] * 11:
                return False

            soma = sum(
                int(cpf[i]) * (10 - i)
                for i in range(9)
            )

            digito1 = (soma * 10) % 11

            if digito1 == 10:
                digito1 = 0

            if digito1 != int(cpf[9]):
                return False

            soma = sum(
                int(cpf[i]) * (11 - i)
                for i in range(10)
            )

            digito2 = (soma * 10) % 11

            if digito2 == 10:
                digito2 = 0

            return digito2 == int(cpf[10])

        if not cpf_valido(cpf):

            erro = "O CPF informado é inválido."

            return render(
                request,
                'accounts/cadastro_participante.html',
                {
                    'erro': erro,
                    'pesquisas': pesquisas
                }
            )

        # Validação da data
        try:

            data_nasc = datetime.strptime(
                data_nascimento,
                "%Y-%m-%d"
            ).date()

            if data_nasc > timezone.now().date():

                erro = "A data de nascimento não pode ser futura."

                return render(
                    request,
                    'accounts/cadastro_participante.html',
                    {
                        'erro': erro,
                        'pesquisas': pesquisas
                    }
                )

        except ValueError:

            erro = "Data de nascimento inválida."

            return render(
                request,
                'accounts/cadastro_participante.html',
                {
                    'erro': erro,
                    'pesquisas': pesquisas
                }
            )

        # Verifica a pesquisa
        pesquisa = Pesquisa.objects.filter(
            id=pesquisa_id,
            responsavel=request.user
        ).first()

        if not pesquisa:

            return HttpResponse(
                "Acesso negado à pesquisa selecionada.",
                status=403
            )

        # Verifica e-mail duplicado
        if Usuario.objects.filter(
            email__iexact=email
        ).exists():

            erro = "Este e-mail já está associado a uma conta."

            return render(
                request,
                'accounts/cadastro_participante.html',
                {
                    'erro': erro,
                    'pesquisas': pesquisas
                }
            )

        # Cria usuário do participante
        usuario = Usuario.objects.create_user(
            username=f"participante_{timezone.now().timestamp()}",
            email=email,
            perfil="participante"
        )

        # Participante ainda não possui senha
        usuario.set_unusable_password()
        usuario.save()

        # Cria participante
        participante = Participante.objects.create(
            registro_participante='TEMP',
            nome_encrypted=encrypt_data(nome),
            cpf_encrypted=encrypt_data(cpf),
            data_nascimento_encrypted=encrypt_data(
                data_nascimento
            ),
            ativo=True,
            usuario=usuario
        )

        participante.registro_participante = (
            f"PT-{participante.id:06d}"
        )

        participante.save(
            update_fields=['registro_participante']
        )

        # Vincula participante à pesquisa
        ParticipacaoPesquisa.objects.create(
            participante=participante,
            pesquisa=pesquisa,
            status='ativo'
        )

        # Cria dispositivo 2FA
        TOTPDevice.objects.get_or_create(
            user=usuario,
            name="Celular Principal",
            defaults={
                'confirmed': False
            }
        )

        # Gera link de ativação
        uid = urlsafe_base64_encode(
            force_bytes(usuario.pk)
        )

        token = default_token_generator.make_token(
            usuario
        )

        link = request.build_absolute_uri(
            reverse(
                'ativar_participante',
                kwargs={
                    'uidb64': uid,
                    'token': token
                }
            )
        )

        # Envia e-mail
        try:

            resposta = requests.post(
                'https://api.brevo.com/v3/smtp/email',

                headers={
                    'accept': 'application/json',
                    'api-key': os.getenv('BREVO_API_KEY'),
                    'content-type': 'application/json',
                },

                json={
                    'sender': {
                        'name': os.getenv('BREVO_SENDER_NAME'),
                        'email': os.getenv('BREVO_SENDER_EMAIL'),
                    },

                    'to': [
                        {
                            'email': email,
                            'name': nome,
                        }
                    ],

                    'subject': 'ClinSecure - Ative sua conta',

                    'textContent': (
                        f'Olá, {nome}.\n\n'
                        'Seu cadastro no ClinSecure foi realizado.\n\n'
                        'Para criar sua senha, acesse o link abaixo:\n\n'
                        f'{link}\n\n'
                        'Após criar sua senha, você poderá entrar '
                        'no ClinSecure utilizando seu e-mail.\n\n'
                        'Se você não esperava este cadastro, '
                        'entre em contato com o responsável pela pesquisa.'
                    ),
                },

                timeout=10,
            )

            resposta.raise_for_status()

        except Exception as e:

            print("===== ERRO AO ENVIAR CONVITE BREVO =====")
            print("TIPO:", type(e).__name__)
            print("ERRO:", e)

            if 'resposta' in locals():
                print("STATUS:", resposta.status_code)
                print("RESPOSTA BREVO:", resposta.text)

            print("=========================================")

            participante.delete()
            usuario.delete()

            erro = (
                "O participante não foi cadastrado porque "
                "não foi possível enviar o e-mail de ativação."
            )

            return render(
                request,
                'accounts/cadastro_participante.html',
                {
                    'erro': erro,
                    'pesquisas': pesquisas
                }
            )

        # Auditoria
        AuditLog.objects.create(
            usuario=request.user,
            evento="Cadastro de participante",
            ip=request.META.get('REMOTE_ADDR'),
            resultado="Sucesso",
            detalhes=(
                f"Participante "
                f"{participante.registro_participante} "
                f"cadastrado e vinculado à pesquisa "
                f"{pesquisa.registro_pesquisa}. "
                f"Dados pessoais criptografados. "
                f"Convite enviado por e-mail."
            )
        )

        return redirect(
            'cadastro_participante'
        )

    return render(
        request,
        'accounts/cadastro_participante.html',
        {
            'erro': erro,
            'pesquisas': pesquisas
        }
    )

def ativar_participante_view(request, uidb64, token):

    from django.utils.http import urlsafe_base64_decode

    try:
        uid = urlsafe_base64_decode(uidb64).decode()

        usuario = Usuario.objects.get(
            pk=uid,
            perfil="participante"
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
        Usuario.DoesNotExist
    ):
        return render(
            request,
            'accounts/ativar_participante.html',
            {
                'validlink': False,
                'erro': 'Link inválido ou expirado.'
            }
        )

    if not default_token_generator.check_token(
        usuario,
        token
    ):
        return render(
            request,
            'accounts/ativar_participante.html',
            {
                'validlink': False,
                'erro': 'Link inválido ou expirado.'
            }
        )

    if request.method == 'POST':

        senha1 = request.POST.get('password', '')
        senha2 = request.POST.get('password_confirm', '')

        if not senha1 or not senha2:
            return render(
                request,
                'accounts/ativar_participante.html',
                {
                    'validlink': True,
                    'erro': 'Preencha os dois campos de senha.'
                }
            )

        if senha1 != senha2:
            return render(
                request,
                'accounts/ativar_participante.html',
                {
                    'validlink': True,
                    'erro': 'As senhas não são iguais.'
                }
            )

        try:
            validate_password(senha1, usuario)
        except ValidationError as e:
            return render(
                request,
                'accounts/ativar_participante.html',
                {
                    'validlink': True,
                    'erro': ' '.join(e.messages)
                }
            )

        usuario.set_password(senha1)
        usuario.save()

        AuditLog.objects.create(
            usuario=usuario,
            evento="Conta de participante ativada",
            ip=request.META.get('REMOTE_ADDR'),
            resultado="Sucesso",
            detalhes=(
                "Participante criou sua senha através "
                "do link de ativação."
            )
        )

        return redirect('login')

    return render(
        request,
        'accounts/ativar_participante.html',
        {
            'validlink': True
        }
    )

## LOGICA DE 2FA ##
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

## LOGICA DE DEFESA DE URL ##
# accounts/views.py
# (Mantenha todos os imports existentes)

@login_required
def home_view(request):
    context = {}
    usuario = request.user
    
    # Administrador e Coordenador veem métricas globais
    if usuario.perfil in ['administrador', 'coordenador']:
        context['total_participantes'] = Participante.objects.filter(ativo=True).count()
        context['pesquisas_ativas'] = Pesquisa.objects.filter(status='ativa').count()
        context['documentos_cadastrados'] = Documento.objects.count()
        context['usuarios_ativos'] = Usuario.objects.filter(is_active=True).count()
        
    # Responsável vê métricas das suas próprias pesquisas e participantes atrelados
    elif usuario.perfil == 'responsavel':
        context['total_participantes'] = Participante.objects.filter(ativo=True, participacoes_pesquisa__pesquisa__responsavel=usuario).distinct().count()
        context['pesquisas_ativas'] = Pesquisa.objects.filter(status='ativa', responsavel=usuario).count()
        context['documentos_cadastrados'] = Documento.objects.filter(responsavel=usuario).count()
        
    # Pesquisador vê métricas gerais das pesquisas e participantes vinculados a pesquisas
    elif usuario.perfil == 'pesquisador':
        context['pesquisas_ativas'] = Pesquisa.objects.filter(status='ativa').count()
        context['total_participantes'] = Participante.objects.filter(ativo=True, participacoes_pesquisa__isnull=False).distinct().count()
        
    # Participante vê métricas estritamente ligadas a ele
    elif usuario.perfil == 'participante':
        context['minhas_pesquisas'] = ParticipacaoPesquisa.objects.filter(participante__usuario=usuario, status='ativo').count()
        context['meus_documentos'] = Documento.objects.filter(participante__usuario=usuario).count()

        participante = Participante.objects.filter(usuario = request.user).first()
        if participante:
            nome_participante = decrypt_data(participante.nome_encrypted)
            context['registro_participante'] = participante.registro_participante
        else:
            nome_participante = request.user.username
        context['nome_participante'] = nome_participante
    return render(request, 'accounts/home.html', context)



## LOGICA DE LOGOUT ##
# Faz o logout do usuário.
def meu_logout_view(request):

    # Encerra a sessão.
    logout(request)

    # Volta para a tela de login.
    return redirect('login')

## LOGICA DE RECUPERAÇÃO DE SENHA ##
def recuperacao_view(request):
    erro = None

    if request.method == 'POST':

        # Captura o valor que pode ser tanto username quanto email
        identificador = request.POST.get('identificador', '').strip()

        if not identificador:
            return render(
                request,
                'accounts/recuperacao.html',
                {'erro': 'Preencha o campo.'}
            )

        # Requisito 2.1: Busca o usuário usando Email OU Username
        usuario = Usuario.objects.filter(
            Q(email=identificador) | Q(username=identificador)
        ).first()

        if usuario:

            # Registra que o usuário solicitou recuperação de senha
            AuditLog.objects.create(
                usuario=usuario,
                evento="Solicitação de recuperação de senha",
                ip=request.META.get('REMOTE_ADDR'),
                resultado="Sucesso",
                detalhes="Usuário solicitou o envio de um link para recuperação de senha."
            )

            # Requisito 2.2: Gera o token criptográfico
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            token = default_token_generator.make_token(usuario)

            # Monta o link absoluto que irá no corpo do e-mail
            link = request.build_absolute_uri(
                reverse(
                    'password_reset_confirm',
                    kwargs={
                        'uidb64': uid,
                        'token': token
                    }
                )
            )

            # Envia o e-mail através da API do Brevo
            try:

                resposta = requests.post(
                    'https://api.brevo.com/v3/smtp/email',

                    headers={
                        'accept': 'application/json',
                        'api-key': os.getenv('BREVO_API_KEY'),
                        'content-type': 'application/json',
                    },

                    json={
                        'sender': {
                            'name': os.getenv('BREVO_SENDER_NAME'),
                            'email': os.getenv('BREVO_SENDER_EMAIL'),
                        },

                        'to': [
                            {
                                'email': usuario.email,
                                'name': usuario.username,
                            }
                        ],

                        'subject': 'ClinSecure - Recuperação de Senha',

                        'textContent': (
                            f'Olá, {usuario.username}.\n\n'
                            'Você solicitou a redefinição de senha.\n\n'
                            'Clique no link abaixo para criar uma nova senha:\n'
                            f'{link}\n\n'
                            'Se não foi você, ignore este e-mail.'
                        ),
                    },

                    timeout=10,
                )

                # Gera exceção caso o Brevo retorne erro HTTP
                resposta.raise_for_status()

            except Exception as e:

                print(
                    f"ERRO BREVO API: {type(e).__name__}: {e}"
                )

                erro = (
                    'Não foi possível enviar o e-mail de recuperação. '
                    'Tente novamente mais tarde.'
                )

                return render(
                    request,
                    'accounts/recuperacao.html',
                    {'erro': erro}
                )

            # Redireciona para a tela de sucesso
            # Evita enumeração de usuários
            return redirect('password_reset_done')

    return render(
        request,
        'accounts/recuperacao.html',
        {'erro': erro}
    )



def confirmar_recuperacao_senha_view(request, uidb64, token):

    # Importa função para decodificar o UID
    from django.utils.http import urlsafe_base64_decode

    # Importa o modelo de usuário
    from django.contrib.auth import get_user_model

    # Pega o modelo de usuário do projeto
    User = get_user_model()

    # Tenta encontrar o usuário
    try:

        # Decodifica o UID recebido
        uid = urlsafe_base64_decode(uidb64).decode()

        # Busca o usuário no banco
        usuario = User.objects.get(pk=uid)

    # Trata UID inválido ou usuário inexistente
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):

        # Mostra que o link é inválido
        return render(
            request,
            'accounts/password_reset_confirm.html',
            {
                'validlink': False,
                'erro': 'Link de recuperação inválido ou expirado.'
            }
        )

    # Verifica se o token ainda é válido
    if not default_token_generator.check_token(usuario, token):

        # Registra a falha no AuditLog
        AuditLog.objects.create(
            usuario=usuario,
            evento="Recuperação com falha — token inválido/expirado",
            ip=request.META.get('REMOTE_ADDR'),
            resultado="Falha",
            detalhes="Tentativa de recuperação de senha utilizando token inválido ou expirado."
        )

        # Mostra mensagem de erro
        return render(
            request,
            'accounts/password_reset_confirm.html',
            {
                'validlink': False,
                'erro': 'Link de recuperação inválido ou expirado.'
            }
        )

    # Verifica se o formulário foi enviado
    if request.method == 'POST':

        # Pega a nova senha
        senha1 = request.POST.get('new_password1')

        # Pega a confirmação da senha
        senha2 = request.POST.get('new_password2')

        # Verifica se os campos foram preenchidos
        if not senha1 or not senha2:

            # Mostra mensagem de erro
            return render(
                request,
                'accounts/password_reset_confirm.html',
                {
                    'validlink': True,
                    'erro': 'Preencha os dois campos de senha.'
                }
            )

        # Verifica se as senhas são iguais
        if senha1 != senha2:

            # Mostra mensagem de erro
            return render(
                request,
                'accounts/password_reset_confirm.html',
                {
                    'validlink': True,
                    'erro': 'As senhas não são iguais.'
                }
            )

        # Define a nova senha
        usuario.set_password(senha1)

        # Salva a nova senha
        usuario.save()

        # Registra a recuperação com sucesso
        AuditLog.objects.create(
            usuario=usuario,
            evento="Recuperação realizada com sucesso",
            ip=request.META.get('REMOTE_ADDR'),
            resultado="Sucesso",
            detalhes="Senha redefinida com sucesso através do processo de recuperação."
        )

        # Vai para a página de conclusão
        return redirect('password_reset_complete')

    # Mostra o formulário de nova senha
    return render(
        request,
        'accounts/password_reset_confirm.html',
        {
            'validlink': True
        }
    )


@login_required
def upload_documento_view(request):
    if request.user.perfil not in [
        "responsavel",
        "administrador",
        "coordenador",
    ]:
        return HttpResponse("Acesso negado.", status=403)

    if request.user.perfil == "responsavel":
        participantes = Participante.objects.filter(
            ativo=True,
            participacoes_pesquisa__pesquisa__responsavel=request.user
        ).distinct()
    else:
        participantes = Participante.objects.filter(
            ativo=True
        )

    if request.method == "GET":
        return render(
            request,
            "accounts/upload_documento.html",
            {"participantes": participantes}
        )

    if request.method != "POST":
        return HttpResponse("Método não permitido.", status=405)

    participante_id = request.POST.get("participante")
    arquivo = request.FILES.get("arquivo")

    if not participante_id or not arquivo:
        return render(
            request,
            "accounts/upload_documento.html",
            {
                "participantes": participantes,
                "erro": "Participante e arquivo são obrigatórios."
            },
            status=400
        )

    nome_arquivo = (arquivo.name or "").strip()
    extensao = os.path.splitext(nome_arquivo)[1].lower()

    # 1. Somente .pdf
    if extensao != ".pdf":
        return render(
            request,
            "accounts/upload_documento.html",
            {
                "participantes": participantes,
                "erro": "Apenas arquivos PDF são permitidos."
            },
            status=400
        )

    # 2. Limite de tamanho
    if arquivo.size > MAX_PDF_SIZE:
        return render(
            request,
            "accounts/upload_documento.html",
            {
                "participantes": participantes,
                "erro": "O arquivo PDF deve ter no máximo 10 MB."
            },
            status=400
        )

    # 3. Verifica a assinatura do arquivo
    cabecalho = arquivo.read(5)
    arquivo.seek(0)

    if cabecalho != b"%PDF-":
        return render(
            request,
            "accounts/upload_documento.html",
            {
                "participantes": participantes,
                "erro": "O arquivo enviado não é um PDF válido."
            },
            status=400
        )


    try:
        participante = Participante.objects.get(
            id=participante_id,
            ativo=True
        )
    except Participante.DoesNotExist:
        return HttpResponse(
            "Participante não encontrado.",
            status=404
        )

    if not usuario_pode_acessar_participante(
        request.user,
        participante
    ):
        return HttpResponse("Acesso negado.", status=403)

    documento = Documento.objects.create(
        participante=participante,
        responsavel=request.user,
        nome_original=arquivo.name,
        arquivo_criptografado=encrypt_file(arquivo),
        status="pendente"
    )

    AuditLog.objects.create(
        usuario=request.user,
        evento="Upload de documento",
        ip=request.META.get("REMOTE_ADDR"),
        resultado="Sucesso",
        detalhes=(
            f"Documento '{arquivo.name}' enviado para "
            f"{participante.registro_participante}."
        )
    )

    return HttpResponse("Documento enviado com sucesso.")



@login_required
def download_documento_view(request, documento_id):

    try:
        documento = Documento.objects.get(id=documento_id)
    except Documento.DoesNotExist:
        return HttpResponse("Documento não encontrado.", status=404)

    if not usuario_pode_acessar_documento(
        request.user,
        documento
    ):
        return HttpResponse("Acesso negado.", status=403)

    try:
        documento.arquivo_criptografado.open("rb")

        arquivo = decrypt_file(
            documento.arquivo_criptografado
        )

        response = HttpResponse(
            arquivo.getvalue(),
            content_type="application/octet-stream"
        )

        response["Content-Disposition"] = (
            f'attachment; filename="{documento.nome_original}"'
        )

        AuditLog.objects.create(
            usuario=request.user,
            evento="Download de documento",
            ip=request.META.get("REMOTE_ADDR"),
            resultado="Sucesso",
            detalhes=(
                f"Documento '{documento.nome_original}' acessado."
            )
        )

        return response

    except Exception:
        return HttpResponse(
            "Erro ao descriptografar o documento.",
            status=500
        )

@login_required
def visualizar_documento_view(request, documento_id):
    
    try:
        documento = Documento.objects.get(id=documento_id)
    except Documento.DoesNotExist:
        return HttpResponse("Documento não encontrado.", status=404)

    if not usuario_pode_acessar_documento(
        request.user,
        documento
    ):
        return HttpResponse("Acesso negado.", status=403)

    try:
        documento.arquivo_criptografado.open("rb")

        arquivo = decrypt_file(
            documento.arquivo_criptografado
        )

        response = HttpResponse(
            arquivo.getvalue(),
            content_type="application/pdf"
        )

        response["Content-Disposition"] = (
            f'inline; filename="{documento.nome_original}"'
        )

        AuditLog.objects.create(
            usuario=request.user,
            evento="visualização de documento",
            ip=request.META.get("REMOTE_ADDR"),
            resultado="Sucesso",
            detalhes=(
                f"Documento '{documento.nome_original}' acessado."
            )
        )

        return response

    except Exception:
        return HttpResponse(
            "Erro ao descriptografar o documento.",
            status=500
        )


@login_required
def conceder_acesso_documento_view(request, documento_id):

    if request.user.perfil != "coordenador":
        return HttpResponse(
            "Acesso negado.",
            status=403
        )
    
    try:
        documento = Documento.objects.get(id=documento_id)
    except Documento.DoesNotExist:
        return HttpResponse("Documento não encontrado.", status=404)

    if not usuario_pode_acessar_participante(
        request.user,
        documento.participante
    ):
        return HttpResponse("Acesso negado.", status=403)

    usuarios = Usuario.objects.filter(
        is_active=True,
        perfil__in=["pesquisador", "responsavel"]
    )

    if request.method == "GET":
        return render(
            request,
            "accounts/conceder_acesso_documento.html",
            {
                "documento": documento,
                "usuarios": usuarios,
            }
        )

    if request.method != "POST":
        return HttpResponse("Método não permitido.", status=405)

    usuario_id = request.POST.get("usuario_id")
    inicio = request.POST.get("inicio_acesso")
    fim = request.POST.get("fim_acesso")

    if not usuario_id or not inicio or not fim:
        return render(
            request,
            "accounts/conceder_acesso_documento.html",
            {
                "documento": documento,
                "usuarios": usuarios,
                "erro": "Usuário, início e fim do acesso são obrigatórios."
            },
            status=400
        )

    try:
        usuario = Usuario.objects.get(
            id=usuario_id,
            is_active=True
        )
    except Usuario.DoesNotExist:
        return HttpResponse(
            "Usuário não encontrado.",
            status=404
        )

    if inicio >= fim:
        return render(
            request,
            "accounts/conceder_acesso_documento.html",
            {
                "documento": documento,
                "usuarios": usuarios,
                "erro": "O fim do acesso deve ser posterior ao início."
            },
            status=400
        )

    Acesso.objects.create(
        documento=documento,
        usuario=usuario,
        concedido_por=request.user,
        inicio_acesso=inicio,
        fim_acesso=fim,
    )

    AuditLog.objects.create(
        usuario=request.user,
        evento="Acesso a documento concedido",
        ip=request.META.get("REMOTE_ADDR"),
        resultado="Sucesso",
        detalhes=(
            f"Acesso ao documento "
            f"'{documento.nome_original}' "
            f"concedido para {usuario.username}."
        )
    )

    return HttpResponse(
        "Acesso concedido com sucesso."
    )



@login_required
def revogar_acesso_documento_view(request, acesso_id):

    if request.method != "POST":
        return HttpResponse(
            "Método não permitido.",
            status=405
        )

    try:
        acesso = Acesso.objects.select_related(
            "documento",
            "documento__participante"
        ).get(id=acesso_id)
    except Acesso.DoesNotExist:
        return HttpResponse(
            "Acesso não encontrado.",
            status=404
        )

    if request.user.perfil not in [
        "responsavel",
        "administrador",
        "coordenador",
    ]:
        return HttpResponse(
            "Acesso negado.",
            status=403
        )

    if not usuario_pode_acessar_participante(
        request.user,
        acesso.documento.participante
    ):
        return HttpResponse(
            "Acesso negado.",
            status=403
        )

    acesso.revogado = True
    acesso.data_revogado = timezone.now()
    acesso.save()

    AuditLog.objects.create(
        usuario=request.user,
        evento="Acesso a documento revogado",
        ip=request.META.get("REMOTE_ADDR"),
        resultado="Sucesso",
        detalhes=(
            f"Acesso ao documento "
            f"'{acesso.documento.nome_original}' revogado."
        )
    )

    return HttpResponse(
        "Acesso revogado com sucesso."
    )

## LOGICA DE PESQUISAS ##

@login_required
@login_required
def lista_pesquisas_view(request):

    context = {}

    usuario = request.user

    if eh_admin_ou_coordenador(usuario):

        pesquisas = Pesquisa.objects.all()

    elif usuario.perfil == "responsavel":

        pesquisas = Pesquisa.objects.filter(
            responsavel=usuario
        )

    elif usuario.perfil == "participante":

        pesquisas = Pesquisa.objects.filter(
            participantes__participante__usuario=usuario
        ).distinct()

        context['minhas_pesquisas'] = (
            ParticipacaoPesquisa.objects.filter(
                participante__usuario=usuario,
                status='ativo'
            ).count()
        )

        context['meus_documentos'] = (
            Documento.objects.filter(
                participante__usuario=usuario
            ).count()
        )

        participante = Participante.objects.filter(
            usuario=request.user
        ).first()

    elif usuario.perfil == "pesquisador":

        # Pesquisador vê somente as pesquisas vinculadas a ele.
        pesquisas = Pesquisa.objects.filter(
            pesquisadores=usuario
        )

    else:

        return HttpResponse(
            "Acesso negado.",
            status=403
        )

    return render(
        request,
        'accounts/pesquisas.html',
        {
            'pesquisas': pesquisas
        }
    )


@login_required
def detalhe_pesquisa_view(request, pesquisa_id):

    try:
        pesquisa = Pesquisa.objects.get(id=pesquisa_id)
    except Pesquisa.DoesNotExist:
        return HttpResponse(
            "Pesquisa não encontrada.",
            status=404
        )

    # Verifica se o usuário pode acessar esta pesquisa.
    if not usuario_pode_acessar_pesquisa(
        request.user,
        pesquisa
    ):
        return HttpResponse(
            "Acesso negado a esta pesquisa.",
            status=403
        )

    # Participante só pode visualizar a própria participação.
    if request.user.perfil == "participante":
        participacoes = (
            ParticipacaoPesquisa.objects
            .filter(
                pesquisa=pesquisa,
                participante__usuario=request.user
            )
            .select_related('participante')
        )

    # Os demais usuários autorizados podem visualizar
    # os participantes da pesquisa.
    else:
        participacoes = (
            ParticipacaoPesquisa.objects
            .filter(pesquisa=pesquisa)
            .select_related('participante')
        )

    return render(
        request,
        'accounts/detalhe_pesquisa.html',
        {
            'pesquisa': pesquisa,
            'participacoes': participacoes,
        }
    )

@login_required
def editar_pesquisa_view(request, pesquisa_id):

    # Busca a pesquisa pelo ID.
    try:
        pesquisa = Pesquisa.objects.get(
            id=pesquisa_id
        )
    except Pesquisa.DoesNotExist:
        return HttpResponse(
            "Pesquisa não encontrada.",
            status=404
        )

    # Somente o responsável da própria pesquisa pode editar.
    if (
        request.user.perfil != "responsavel"
        or pesquisa.responsavel_id != request.user.id
    ):
        return HttpResponse(
            "Acesso negado. Você não pode editar esta pesquisa.",
            status=403
        )

    erro = None

    if request.method == "POST":

        nome = request.POST.get(
            "nome",
            ""
        ).strip()

        descricao = request.POST.get(
            "descricao",
            ""
        ).strip()

        status = request.POST.get(
            "status",
            ""
        ).strip()

        data_inicio = request.POST.get(
            "data_inicio",
            ""
        ).strip()

        data_fim = request.POST.get(
            "data_fim",
            ""
        ).strip()

        # Verifica o nome.
        if not nome:
            erro = "O nome da pesquisa é obrigatório."

        # Verifica o status.
        elif status not in [
            "planejamento",
            "ativa",
            "encerrada",
            "cancelada",
        ]:
            erro = "Status da pesquisa inválido."

        # Verifica as datas.
        elif data_inicio and data_fim:
            try:
                inicio = datetime.strptime(
                    data_inicio,
                    "%Y-%m-%d"
                ).date()

                fim = datetime.strptime(
                    data_fim,
                    "%Y-%m-%d"
                ).date()

                if fim < inicio:
                    erro = (
                        "A data de fim não pode ser anterior "
                        "à data de início."
                    )

            except ValueError:
                erro = "Informe datas válidas."

        # Salva as alterações.
        if not erro:

            pesquisa.nome = nome
            pesquisa.descricao = descricao
            pesquisa.status = status
            pesquisa.data_inicio = (
                data_inicio or None
            )
            pesquisa.data_fim = (
                data_fim or None
            )

            pesquisa.save()

            # Registra a alteração no histórico.
            AuditLog.objects.create(
                usuario=request.user,
                evento="Edição de pesquisa",
                ip=request.META.get("REMOTE_ADDR"),
                resultado="Sucesso",
                detalhes=(
                    f"Pesquisa {pesquisa.registro_pesquisa} "
                    f"editada pelo responsável."
                )
            )

            return redirect(
                "detalhe_pesquisa",
                pesquisa_id=pesquisa.id
            )

    return render(
        request,
        "accounts/editar_pesquisa.html",
        {
            "pesquisa": pesquisa,
            "erro": erro,
        }
    )

@login_required
def cadastrar_dado_pesquisa_view(request, participacao_id):

    try:
        participacao = ParticipacaoPesquisa.objects.select_related(
            'participante',
            'pesquisa'
        ).get(id=participacao_id)

    except ParticipacaoPesquisa.DoesNotExist:
        return HttpResponse(
            "Participação não encontrada.",
            status=404
        )

    # Verifica se o usuário pode acessar a pesquisa.
    if not usuario_pode_acessar_pesquisa(
        request.user,
        participacao.pesquisa
    ):
        return HttpResponse(
            "Acesso negado.",
            status=403
        )

    # Apenas responsáveis, pesquisadores,
    # administradores e coordenadores podem registrar dados.
    if request.user.perfil not in [
        "responsavel",
        "pesquisador",
        "administrador",
        "coordenador",
    ]:
        return HttpResponse(
            "Acesso negado.",
            status=403
        )

    erro = None

 # Verifica se o participante possui consentimento ativo.
    consentimento_ativo = Consentimento.objects.filter(
        participante=participacao.participante,
        finalidade=FINALIDADE_CONSENTIMENTO,
        versao=VERSAO_CONSENTIMENTO,
        revogado=False
    ).exists()

    if request.method == 'POST' and not consentimento_ativo:
        erro = (
            "Não é possível cadastrar dados de pesquisa "
            "porque o participante não possui consentimento ativo."
        )

    elif request.method == 'POST':

        tipo = request.POST.get('tipo', '').strip()
        data_coleta = request.POST.get('data_coleta', '').strip()
        resultado = request.POST.get('resultado', '').strip()

        if not tipo or not resultado:
            erro = "Preencha o tipo e o resultado."

        else:

            DadoPesquisa.objects.create(
                participacao=participacao,
                tipo=tipo,
                data_coleta=data_coleta or None,
                resultado_encrypted=encrypt_data(resultado)
            )

            AuditLog.objects.create(
                usuario=request.user,
                evento="Cadastro de dado de pesquisa",
                ip=request.META.get('REMOTE_ADDR'),
                resultado="Sucesso",
                detalhes=(
                    f"Dado '{tipo}' cadastrado para "
                    f"{participacao.participante.registro_participante} "
                    f"na pesquisa "
                    f"{participacao.pesquisa.registro_pesquisa}. "
                    f"Resultado armazenado criptografado."
                )
            )

            return redirect(
                'detalhe_participante',
                participante_id=participacao.participante.id
            )

    return render(
        request,
        'accounts/cadastrar_dado_pesquisa.html',
        {
            'participacao': participacao,
            'erro': erro,
        }
    )

@login_required
def detalhe_participante_view(request, participante_id):

    try:
        participante = Participante.objects.get(
            id=participante_id
        )
    except Participante.DoesNotExist:
        return HttpResponse(
            "Participante não encontrado.",
            status=404
        )

    # Verifica se o usuário pode acessar este participante.
    if not usuario_pode_acessar_participante(
        request.user,
        participante
    ):
        return HttpResponse(
            "Acesso negado a este participante.",
            status=403
        )

    # Pesquisas das quais o participante faz parte.
    participacoes = ParticipacaoPesquisa.objects.filter(
        participante=participante
    ).select_related(
        'pesquisa'
    )

    # Dados científicos/exames do participante.
    dados = DadoPesquisa.objects.filter(
        participacao__participante=participante
    )

    # Pesquisador: somente dados das pesquisas às quais
    # o pesquisador está vinculado.
    if request.user.perfil == "pesquisador":
        dados = dados.filter(
            participacao__pesquisa__pesquisadores=request.user
        )

    dados = dados.select_related(
        'participacao',
        'participacao__pesquisa'
    ).order_by(
        '-data_coleta',
        '-data_cadastro'
    )

    # Descriptografa a data de nascimento apenas
    # para calcular a faixa etária.
    try:
        data_nascimento = decrypt_data(
            participante.data_nascimento_encrypted
        )

        ano_nascimento = int(
            data_nascimento[:4]
        )

        hoje = timezone.now().date()

        # Calcula a idade considerando mês/dia.
        ano, mes, dia = map(
            int,
            data_nascimento.split('-')
        )

        idade = hoje.year - ano

        if (hoje.month, hoje.day) < (mes, dia):
            idade -= 1

        faixa_inicio = (idade // 10) * 10
        faixa_fim = faixa_inicio + 9

        faixa_etaria = (
            f"{faixa_inicio}–{faixa_fim} anos"
        )

    except Exception:
        faixa_etaria = "Não disponível"

    # Descriptografa os resultados somente
    # depois que o usuário foi autorizado.
    dados_exibicao = []

    for dado in dados:

        try:
            resultado = decrypt_data(
                dado.resultado_encrypted
            )
        except Exception:
            resultado = "Resultado indisponível"

        dados_exibicao.append({
            'tipo': dado.tipo,
            'data_coleta': dado.data_coleta,
            'resultado': resultado,
            'pesquisa': dado.participacao.pesquisa,
        })

    documentos = Documento.objects.filter(
        participante=participante
    )

    acessos_documentos = Acesso.objects.filter(
        documento__participante=participante,
        revogado=False
    ).select_related(
        "documento",
        "usuario"
    )

    return render(
        request,
        'accounts/detalhe_participante.html',
        {
            'participante': participante,
            'participacoes': participacoes,
            'dados': dados_exibicao,
            'faixa_etaria': faixa_etaria,
            'documentos': documentos,
            "now": timezone.now(),
            'acessos_documentos': acessos_documentos,
        }
    )

def normalizar_cpf(cpf):
    return re.sub(r'\D', '', cpf)


from .models import (
    Usuario,
    AuditLog,
    Participante,
    Consentimento,
    ParticipacaoPesquisa,
    Documento,
)
from .crypto import decrypt_data, encrypt_data


FINALIDADE_CONSENTIMENTO = (
    "Gerenciamento e participação em pesquisas clínicas."
)

VERSAO_CONSENTIMENTO = "1.0"


@login_required
def meus_dados_view(request):
    if request.user.perfil != "participante":
        return HttpResponse("Acesso negado.", status=403)

    participante = get_object_or_404(
        Participante,
        usuario=request.user
    )

    consentimentos = participante.consentimentos.order_by(
        "-data_consentimento"
    )

    participacoes = (
        ParticipacaoPesquisa.objects
        .filter(participante=participante)
        .select_related("pesquisa")
    )

    documentos = (
        participante.documentos
        .only("id", "nome_original", "data_upload", "status")
        .order_by("-data_upload")
    )

    contexto = {
        "participante": participante,
        "nome": decrypt_data(participante.nome_encrypted),
        "cpf": decrypt_data(participante.cpf_encrypted),
        "data_nascimento": decrypt_data(
            participante.data_nascimento_encrypted
        ),
        "consentimentos": consentimentos,
        "participacoes": participacoes,
        "documentos": documentos,
        "consentimento_ativo": consentimentos.filter(
            revogado=False
        ).first(),
        "finalidade_consentimento": FINALIDADE_CONSENTIMENTO,
    }

    return render(
        request,
        "accounts/meus_dados.html",
        contexto
    )


@login_required
def consentir_dados_view(request):
    if request.user.perfil != "participante":
        return HttpResponse("Acesso negado.", status=403)

    if request.method != "POST":
        return redirect("meus_dados")

    aceito = request.POST.get("consentimento")

    if aceito != "sim":
        return render(
            request,
            "accounts/meus_dados.html",
            {
                "erro": "É necessário aceitar explicitamente o consentimento."
            },
            status=400
        )

    participante = get_object_or_404(
        Participante,
        usuario=request.user
    )

    consentimento_existente = Consentimento.objects.filter(
        participante=participante,
        finalidade=FINALIDADE_CONSENTIMENTO,
        versao=VERSAO_CONSENTIMENTO,
        revogado=False
    ).first()

    if consentimento_existente:
        return redirect("meus_dados")

    consentimento = Consentimento.objects.create(
        participante=participante,
        registrado_por=request.user,
        finalidade=FINALIDADE_CONSENTIMENTO,
        versao=VERSAO_CONSENTIMENTO
    )

    AuditLog.objects.create(
        usuario=request.user,
        evento="Consentimento registrado",
        ip=request.META.get("REMOTE_ADDR"),
        resultado="Sucesso",
        detalhes=(
            f"Consentimento registrado. "
            f"Finalidade: {consentimento.finalidade}. "
            f"Versão: {consentimento.versao}."
        )
    )

    return redirect("meus_dados")


@login_required
def revogar_consentimento_view(request, consentimento_id):
    if request.user.perfil != "participante":
        return HttpResponse("Acesso negado.", status=403)

    participante = get_object_or_404(
        Participante,
        usuario=request.user
    )

    consentimento = get_object_or_404(
        Consentimento,
        id=consentimento_id,
        participante=participante
    )

    if request.method != "POST":
        return redirect("meus_dados")

    if consentimento.revogado:
        return redirect("meus_dados")

    consentimento.revogado = True
    consentimento.data_revogado = timezone.now()
    consentimento.save(
        update_fields=["revogado", "data_revogado"]
    )

    AuditLog.objects.create(
        usuario=request.user,
        evento="Consentimento revogado",
        ip=request.META.get("REMOTE_ADDR"),
        resultado="Sucesso",
        detalhes=(
            f"Consentimento revogado. "
            f"Finalidade: {consentimento.finalidade}. "
            f"Versão: {consentimento.versao}."
        )
    )

    return redirect("meus_dados")


@login_required
def exportar_dados_view(request):
    if request.user.perfil != "participante":
        return HttpResponse("Acesso negado.", status=403)

    participante = get_object_or_404(
        Participante,
        usuario=request.user
    )

    consentimentos = []

    for consentimento in participante.consentimentos.order_by(
        "data_consentimento"
    ):
        consentimentos.append({
            "finalidade": consentimento.finalidade,
            "versao": consentimento.versao,
            "data_consentimento": (
                consentimento.data_consentimento.isoformat()
                if consentimento.data_consentimento
                else None
            ),
            "revogado": consentimento.revogado,
            "data_revogado": (
                consentimento.data_revogado.isoformat()
                if consentimento.data_revogado
                else None
            ),
        })

    participacoes = []

    for participacao in (
        ParticipacaoPesquisa.objects
        .filter(participante=participante)
        .select_related("pesquisa")
    ):
        participacoes.append({
            "pesquisa": participacao.pesquisa.nome,
            "registro_pesquisa": participacao.pesquisa.registro_pesquisa,
            "status": participacao.status,
            "data_entrada": (
                participacao.data_entrada.isoformat()
                if participacao.data_entrada
                else None
            ),
            "data_saida": (
                participacao.data_saida.isoformat()
                if participacao.data_saida
                else None
            ),
        })

    documentos = []

    for documento in participante.documentos.all():
        documentos.append({
            "nome_original": documento.nome_original,
            "data_upload": (
                documento.data_upload.isoformat()
                if documento.data_upload
                else None
            ),
            "status": documento.status,
        })

    dados = {
        "dados_pessoais": {
            "nome": decrypt_data(participante.nome_encrypted),
            "cpf": decrypt_data(participante.cpf_encrypted),
            "data_nascimento": decrypt_data(
                participante.data_nascimento_encrypted
            ),
            "email": request.user.email,
            "registro_participante": (
                participante.registro_participante
            ),
        },
        "consentimentos": consentimentos,
        "participacoes_em_pesquisas": participacoes,
        "documentos": documentos,
    }

    AuditLog.objects.create(
        usuario=request.user,
        evento="Exportação de dados",
        ip=request.META.get("REMOTE_ADDR"),
        resultado="Sucesso",
        detalhes="Titular exportou seus dados pessoais."
    )

    resposta = HttpResponse(
        json.dumps(
            dados,
            ensure_ascii=False,
            indent=2,
            default=str
        ),
        content_type="application/json; charset=utf-8"
    )

    resposta["Content-Disposition"] = (
        'attachment; filename="meus_dados_clinsecure.json"'
    )

    return resposta


@login_required
def excluir_dados_view(request):
    if request.user.perfil != "participante":
        return HttpResponse("Acesso negado.", status=403)

    if request.method != "POST":
        return redirect("meus_dados")

    participante = get_object_or_404(
        Participante,
        usuario=request.user
    )

    usuario = request.user

    # Remove os dados pessoais identificáveis,
    # preservando apenas a estrutura necessária
    # para rastreabilidade e integridade do sistema.
    participante.nome_encrypted = encrypt_data(
        "DADO_REMOVIDO"
    )
    participante.cpf_encrypted = encrypt_data(
        "DADO_REMOVIDO"
    )
    participante.data_nascimento_encrypted = encrypt_data(
        "DADO_REMOVIDO"
    )
    participante.ativo = False
    participante.save(
        update_fields=[
            "nome_encrypted",
            "cpf_encrypted",
            "data_nascimento_encrypted",
            "ativo",
        ]
    )

    usuario.email = ""
    usuario.is_active = False
    usuario.set_unusable_password()
    usuario.username = f"anonimizado_{usuario.id}"
    usuario.save(
        update_fields=[
            "email",
            "is_active",
            "password",
            "username",
        ]
    )

    # Remove o dispositivo TOTP associado.
    from django_otp.plugins.otp_totp.models import TOTPDevice

    TOTPDevice.objects.filter(
        user=usuario
    ).delete()

    AuditLog.objects.create(
        usuario=None,
        evento="Exclusão de dados pessoais",
        ip=request.META.get("REMOTE_ADDR"),
        resultado="Sucesso",
        detalhes=(
            "Dados pessoais do titular foram removidos/"
            "anonimizados conforme o fluxo de atendimento."
        )
    )

    logout(request)

    return redirect("login")

@login_required
def analise_logs_view(request):
    # Somente administrador e coordenador podem analisar os logs.
    if request.user.perfil not in ['administrador', 'coordenador']:
        return HttpResponse("Acesso negado.", status=403)

    # Conta quantas vezes cada evento aconteceu.
    eventos = (
        AuditLog.objects
        .values('evento')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # Conta os resultados dos eventos.
    resultados = (
        AuditLog.objects
        .values('resultado')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # Busca os últimos 20 registros.
    ultimos_logs = (
        AuditLog.objects
        .select_related('usuario')
        .order_by('-data_hora')[:20]
    )

    contexto = {
        'eventos': eventos,
        'resultados': resultados,
        'ultimos_logs': ultimos_logs,
    }

    return render(
        request,
        'accounts/analise_logs.html',
        contexto
    )