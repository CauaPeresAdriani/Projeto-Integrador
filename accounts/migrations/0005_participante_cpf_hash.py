from django.db import migrations, models

from accounts.crypto import decrypt_data, gerar_hash_cpf


def preencher_cpf_hash(apps, schema_editor):
    """Gera o hash dos participantes já cadastrados."""
    Participante = apps.get_model('accounts', 'Participante')
    vistos = set()

    for p in Participante.objects.filter(cpf_hash__isnull=True).iterator():
        try:
            cpf = decrypt_data(p.cpf_encrypted)
        except Exception:
            continue

        # Pula registros anonimizados ("DADO_REMOVIDO") ou inválidos.
        if not cpf or not cpf.isdigit() or len(cpf) != 11:
            continue

        h = gerar_hash_cpf(cpf)

        # Se já existir CPF duplicado no banco, mantém só o primeiro.
        if h in vistos:
            continue
        vistos.add(h)

        Participante.objects.filter(pk=p.pk).update(cpf_hash=h)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_auditlog_hash_anterior_auditlog_hash_integridade'),
    ]

    operations = [
        migrations.AddField(
            model_name='participante',
            name='cpf_hash',
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(preencher_cpf_hash, migrations.RunPython.noop),
    ]