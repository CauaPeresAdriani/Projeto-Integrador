from cryptography.fernet import Fernet
from django.conf import settings


def encrypt_data(data):
    """
    Criptografa um dado utilizando a chave protegida
    configurada nas variáveis de ambiente.
    """

    if data is None:
        return None

    fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)

    encrypted_data = fernet.encrypt(data.encode("utf-8"))

    return encrypted_data.decode("utf-8")


def decrypt_data(encrypted_data):
    """
    Descriptografa um dado utilizando a chave protegida
    configurada nas variáveis de ambiente.
    """

    if encrypted_data is None:
        return None

    fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)

    decrypted_data = fernet.decrypt(
        encrypted_data.encode("utf-8")
    )

    return decrypted_data.decode("utf-8")