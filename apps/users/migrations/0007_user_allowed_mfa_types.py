from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_user_ukey_sn'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='allowed_mfa_types',
            field=models.JSONField(blank=True, default=list, verbose_name='Allowed MFA types'),
        ),
    ]
