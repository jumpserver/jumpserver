import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('authentication', '0011_connectiontoken_date_last_used')]

    operations = [migrations.CreateModel(
        name='RDPLoginTicket',
        fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('connection_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ('org_id', models.UUIDField()),
            ('user_id', models.UUIDField()),
            ('asset_id', models.UUIDField()),
            ('host_id', models.UUIDField()),
            ('app_id', models.UUIDField()),
            ('app_name', models.CharField(max_length=128)),
            ('username', models.CharField(max_length=20, unique=True)),
            ('password_hash', models.CharField(max_length=64)),
            ('expires_at', models.DateTimeField()),
            ('redeemed_at', models.DateTimeField(null=True)),
            ('redeemed_by_id', models.UUIDField(null=True)),
            ('redemption_id', models.UUIDField(null=True)),
            ('broker_instance_id', models.UUIDField(null=True)),
            ('windows_session_id', models.PositiveBigIntegerField(null=True)),
            ('grant_hash', models.CharField(max_length=64, null=True, unique=True)),
            ('login_deadline', models.DateTimeField(null=True)),
            ('launch_deadline', models.DateTimeField(null=True)),
            ('launched_at', models.DateTimeField(null=True)),
            ('request_id', models.UUIDField(null=True)),
            ('local_sid', models.CharField(blank=True, max_length=184)),
            ('logon_id', models.CharField(blank=True, max_length=64)),
            ('connection_token', models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='rdp_login_tickets', to='authentication.connectiontoken',
            )),
        ],
        options={
            'default_permissions': (),
            'constraints': [models.UniqueConstraint(
                fields=('redeemed_by_id', 'redemption_id'), name='rdp_login_unique_redemption',
            )],
        },
    )]
