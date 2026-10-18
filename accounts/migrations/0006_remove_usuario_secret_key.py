from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_participante_cpf_hash'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usuario',
            name='secret_key',
        ),
    ]