from django.utils import timezone
from .models import (
    Usuario,
    Pesquisa,
    Participante,
    ParticipacaoPesquisa,
    Documento,
    Acesso,
)


def eh_admin_ou_coordenador(usuario):
    return (
        usuario.is_authenticated
        and usuario.perfil in ["administrador", "coordenador"]
    )


def usuario_pode_acessar_pesquisa(usuario, pesquisa):
    if not usuario.is_authenticated:
        return False

    if eh_admin_ou_coordenador(usuario):
        return True

    # Responsável: somente suas próprias pesquisas
    if usuario.perfil == "responsavel":
        return pesquisa.responsavel_id == usuario.id

    # Participante: somente pesquisas das quais participa
    if usuario.perfil == "participante":
        return ParticipacaoPesquisa.objects.filter(
            pesquisa=pesquisa,
            participante__usuario=usuario
        ).exists()

    # Pesquisador
    if usuario.perfil == "pesquisador":
        return True

    return False


def usuario_pode_acessar_participante(usuario, participante):
    if not usuario.is_authenticated:
        return False

    if eh_admin_ou_coordenador(usuario):
        return True

    # O próprio participante
    if (
        usuario.perfil == "participante"
        and participante.usuario_id == usuario.id
    ):
        return True

    # Responsável: participante precisa estar em uma de suas pesquisas
    if usuario.perfil == "responsavel":
        return ParticipacaoPesquisa.objects.filter(
            participante=participante,
            pesquisa__responsavel=usuario
        ).exists()

    # Pesquisador
    if usuario.perfil == "pesquisador":
        return ParticipacaoPesquisa.objects.filter(
            participante=participante
        ).exists()

    return False


def usuario_pode_acessar_documento(usuario, documento):
    if not usuario.is_authenticated:
        return False

    if eh_admin_ou_coordenador(usuario):
        return True

    # O participante pode acessar documento próprio
    if (
        usuario.perfil == "participante"
        and documento.participante.usuario_id == usuario.id
    ):
        return True

    # Para os demais usuários, precisa existir Acesso válido
    agora = timezone.now()

    return Acesso.objects.filter(
        documento=documento,
        usuario=usuario,
        revogado=False,
        inicio_acesso__lte=agora,
        fim_acesso__gte=agora
    ).exists()
