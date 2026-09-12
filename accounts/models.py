from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class Usuario(AbstractUser):

    perfil = models.CharField(
        max_length=20,
        choices=[
            ('coordenador', 'Coordenador'),
            ('pesquisador', 'Pesquisador'),
            ('administrador', 'Administrador'),
            ('responsavel', 'Responsável'),
            ('participante', 'Participante'),
        ]
    )

    REQUIRED_FIELDS = ['email', 'perfil']

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
    registro_participante = models.CharField(
        max_length=30,
        unique=True
    )

    nome_encrypted = models.TextField()

    cpf_encrypted = models.TextField()

    data_nascimento_encrypted = models.TextField()

    ativo = models.BooleanField(default=True)

    data_cadastro = models.DateTimeField(auto_now_add=True)

    usuario = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="participante"
)

    def __str__(self):
        return self.registro_participante



class Pesquisa(models.Model):
    registro_pesquisa = models.CharField(
        max_length=30,
        unique=True
    )

    nome = models.CharField(max_length=150)

    descricao = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('planejamento', 'Planejamento'),
            ('ativa', 'Ativa'),
            ('encerrada', 'Encerrada'),
            ('cancelada', 'Cancelada'),
        ],
        default='planejamento'
    )

    data_inicio = models.DateField(
        null=True,
        blank=True
    )

    data_fim = models.DateField(
        null=True,
        blank=True
    )

    responsavel = models.ForeignKey(
    Usuario,
    on_delete=models.PROTECT,
    related_name='pesquisas_responsavel',
    limit_choices_to={'perfil': 'responsavel'}
    )

    def __str__(self):
        return self.registro_pesquisa


class ParticipacaoPesquisa(models.Model):
    participante = models.ForeignKey(
        Participante,
        on_delete=models.CASCADE,
        related_name='participacoes_pesquisa'
    )

    pesquisa = models.ForeignKey(
        Pesquisa,
        on_delete=models.CASCADE,
        related_name='participantes'
    )

    data_entrada = models.DateField(
        auto_now_add=True
    )

    data_saida = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('ativo', 'Ativo'),
            ('concluido', 'Concluído'),
            ('retirado', 'Retirado'),
        ],
        default='ativo'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['participante', 'pesquisa'],
                name='unique_participante_pesquisa'
            )
        ]

    def __str__(self):
        return (
            f"{self.participante.registro_participante} - "
            f"{self.pesquisa.registro_pesquisa}"
        )


class DadoPesquisa(models.Model):

    participacao = models.ForeignKey(
        ParticipacaoPesquisa,
        on_delete=models.CASCADE,
        related_name='dados'
    )

    tipo = models.CharField(
        max_length=100
    )

    data_coleta = models.DateField(
        null=True,
        blank=True
    )

    resultado_encrypted = models.TextField()

    data_cadastro = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.tipo} - "
            f"{self.participacao.participante.registro_participante}"
        )    

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
        f"Consentimento de {self.participante.registro_participante} "
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
            f"{self.participante.registro_participante}"
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