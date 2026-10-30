import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0014_clientloginsession'),
    ]

    operations = [
        migrations.AddField(
            model_name='connectiontoken',
            name='client_login_session',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='connection_tokens',
                to='authentication.clientloginsession',
                verbose_name='Client login session',
            ),
        ),
    ]
