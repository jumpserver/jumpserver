from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0009_connectiontoken_input_secret_type'),
        ('accounts', '0011_personalassetcredential'),
    ]

    operations = [
        migrations.AddField(
            model_name='connectiontoken',
            name='personal_credential_id',
            field=models.UUIDField(
                blank=True, null=True,
                verbose_name='Personal credential ID',
            ),
        ),
        migrations.AddField(
            model_name='connectiontoken',
            name='personal_credential_version',
            field=models.PositiveIntegerField(
                blank=True, null=True,
                verbose_name='Personal credential version',
            ),
        ),
    ]
