from django.db import models
from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    cpf = models.CharField(max_length=11, unique=True)

    perfil = models.CharField(
        max_length=20,
        choices=[
            ('coordenador', 'Coordenador'),
            ('pesquisador', 'Pesquisador'),
            ('administrador', 'Administrador'),
            ('responsavel', 'Responsável'),
        ]
    )

    REQUIRED_FIELDS = ['email', 'cpf', 'perfil']

    # 2FA
    dois_fatores_ativado = models.BooleanField(default=False)
    secret_key = models.CharField(max_length=32, blank=True, null=True)

    # Proteção contra brute force
    tentativas_login = models.PositiveIntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)
    ultimo_login_falhou = models.DateTimeField(null=True, blank=True)

    # Proteção do 2FA
    tentativas_2fa = models.PositiveIntegerField(default=0)
    bloqueado_2fa_ate = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username


class AuditLog(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs_auditoria'
    )

    evento = models.CharField(max_length=100)
    data_hora = models.DateTimeField(auto_now_add=True)

    ip = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    resultado = models.CharField(max_length=100)
    detalhes = models.TextField()

    def __str__(self):
        usuario = self.usuario.username if self.usuario else 'Sistema'
        return f"{usuario} - {self.evento} - {self.data_hora}"


class Participante(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=11, unique=True)
    data_nascimento = models.DateField()

    ativo = models.BooleanField(default=True)

    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class Consentimento(models.Model):
    participante = models.ForeignKey(
        Participante,
        on_delete=models.CASCADE,
        related_name='consentimentos'
    )

    registrado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='consentimentos_registrados'
    )

    finalidade = models.CharField(max_length=100)

    versao = models.CharField(max_length=20)

    data_consentimento = models.DateTimeField(
        auto_now_add=True
    )

    revogado = models.BooleanField(default=False)

    data_revogado = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"Consentimento de {self.participante.nome} "
            f"- versão {self.versao}"
        )


class Documento(models.Model):
    participante = models.ForeignKey(
        Participante,
        on_delete=models.CASCADE,
        related_name='documentos'
    )

    responsavel = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='documentos_responsavel'
    )

    nome_original = models.CharField(max_length=255)

    arquivo_criptografado = models.FileField(
        upload_to='documentos_criptografados/'
    )

    data_upload = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('pendente', 'Pendente'),
            ('aprovado', 'Aprovado'),
            ('rejeitado', 'Rejeitado'),
        ],
        default='pendente'
    )

    def __str__(self):
        return (
            f"{self.nome_original} - "
            f"{self.participante.nome}"
        )


class Acesso(models.Model):
    documento = models.ForeignKey(
        Documento,
        on_delete=models.CASCADE,
        related_name='acessos'
    )

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='acessos_documentos'
    )

    concedido_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='acessos_concedidos'
    )

    inicio_acesso = models.DateTimeField()
    fim_acesso = models.DateTimeField()

    revogado = models.BooleanField(default=False)

    data_revogado = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"Acesso de {self.usuario.username} "
            f"ao documento {self.documento.nome_original}"
        )