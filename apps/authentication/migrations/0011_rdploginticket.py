import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('authentication', '0010_connectiontoken_personal_credential_id')]

    operations = [migrations.CreateModel(
        name='RDPLoginTicket',
        fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('host_id', models.UUIDField()),
            ('app_name', models.CharField(max_length=128)),
            ('ticket_hash', models.CharField(max_length=64, unique=True)),
            ('expires_at', models.DateTimeField()),
            ('consumed_at', models.DateTimeField(null=True)),
            ('grant_hash', models.CharField(max_length=64, null=True, unique=True)),
            ('grant_expires_at', models.DateTimeField(null=True)),
            ('launched_at', models.DateTimeField(null=True)),
            ('connection_token', models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='rdp_login_ticket', to='authentication.connectiontoken',
            )),
        ],
        options={'default_permissions': ()},
    )]
