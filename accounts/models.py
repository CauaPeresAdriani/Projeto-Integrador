from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    cpf = models.CharField(max_length=11, unique=True)
    perfil = models.CharField(max_length=20, choices=[
        ('coordenador', 'Coordenador'),
        ('aluno', 'Aluno'),
        ('professor', 'Professor'),
        ('administrador', 'Administrador'),
        ('responsavel', 'Responsável'),])

    REQUIRED_FIELDS = ['email', 'cpf', 'perfil']

    
    dois_fatores_ativado = models.BooleanField(default=False)
    secret_key = models.CharField(max_length=32, blank=True, null=True)
    

    def __str__(self):
        return self.username
# Create your models here.


class Aluno(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=11, unique=True)
    data_nascimento = models.DateField()

    def __str__(self):
        return self.nome

class AuditLog(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    evento = models.CharField(max_length=100)
    data_hora = models.DateTimeField(auto_now_add=True)
    ip = models.CharField(max_length=100)
    resultado = models.CharField(max_length=100)
    detalhes = models.TextField()

    def __str__(self):
        return f"{self.usuario.username} - {self.evento} - {self.data_hora}"

class Consentimento(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    finalidade = models.CharField(max_length=100)
    versao = models.CharField(max_length=10)
    data_consentimento = models.DateField(auto_now_add=True)
    revogado = models.BooleanField(default=False)
    data_revogado = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Consentimento de {self.usuario.username} para {self.aluno.nome}"

class Documento(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    responsavel_id = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    nome_original = models.CharField(max_length=255)
    arquivo_criptografado = models.FileField(upload_to='documentos_criptografados/')
    data_upload = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('pendente', 'Pendente'), ('aprovado', 'Aprovado'), ('rejeitado', 'Rejeitado')], default='pendente')

    def __str__(self):
        return f"{self.nome_original} de {self.responsavel_id.username} para {self.aluno.nome}"

class Acesso(models.Model):
    documento_id = models.ForeignKey(Documento, on_delete=models.CASCADE)
    usuario_id = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    concedido_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='concedido_por')
    inicio_acesso = models.DateTimeField()
    fim_acesso = models.DateTimeField()
    revogado = models.BooleanField(default=False)
    data_revogado = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Acesso de {self.usuario_id.username} ao documento {self.documento_id.nome_original}"