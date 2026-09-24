import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('users', '0006_user_ukey_sn')]

    operations = [
        migrations.CreateModel(
            name='UKeyCertificateBinding',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                    primary_key=True, related_name='ukey_certificate_binding', serialize=False, to='users.user')),
                ('provider', models.CharField(default='xjca', editable=False, max_length=16)),
                ('issuer_fingerprint', models.CharField(max_length=64)),
                ('serial_number', models.CharField(max_length=64)),
                ('certificate_fingerprint', models.CharField(max_length=64, unique=True)),
                ('hardware_serial', models.CharField(max_length=128)),
                ('version', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'UKey certificate binding',
                'constraints': [models.UniqueConstraint(
                    fields=('provider', 'issuer_fingerprint', 'serial_number'),
                    name='users_ukey_unique_certificate',
                )],
            },
        ),
    ]
