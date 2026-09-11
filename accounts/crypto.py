from cryptography.fernet import Fernet
from django.conf import settings


def encrypt_data(data):


    if data is None:
        return None

    fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)

    encrypted_data = fernet.encrypt(data.encode("utf-8"))

    return encrypted_data.decode("utf-8")


def decrypt_data(encrypted_data):


    if encrypted_data is None:
        return None

    fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)

    decrypted_data = fernet.decrypt(
        encrypted_data.encode("utf-8")
    )

    return decrypted_data.decode("utf-8")


from io import BytesIO
from django.core.files.base import ContentFile


def encrypt_file(file):

    if file is None:
        return None

    fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)

    conteudo = file.read()

    conteudo_criptografado = fernet.encrypt(conteudo)

    return ContentFile(
        conteudo_criptografado,
        name=file.name
    )


def decrypt_file(file):


    if file is None:
        return None

    fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)

    conteudo = file.read()

    conteudo_descriptografado = fernet.decrypt(conteudo)

    return BytesIO(conteudo_descriptografado)