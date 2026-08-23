from django.contrib.auth.hashers import Argon2PasswordHasher


class CustoHash(Argon2PasswordHasher):
    time_cost = 4
    memory_cost = 128 * 1024
    parallelism = 2