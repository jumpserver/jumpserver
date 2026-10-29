import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from oauth2_provider.settings import oauth2_settings


class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0013_connectiontoken_shared_review'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        migrations.swappable_dependency(oauth2_settings.APPLICATION_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='ClientLoginSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('token_family', models.UUIDField()),
                ('authenticated_at', models.DateTimeField()),
                ('last_activity_at', models.DateTimeField()),
                ('revoked_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('revoke_reason', models.CharField(blank=True, default='', max_length=32, choices=[
                    ('logout', 'Logout'), ('app_exit', 'Client exit'), ('idle_timeout', 'Idle timeout'),
                    ('absolute_timeout', 'Maximum login time'), ('policy_changed', 'Client login policy changed'),
                    ('security_revoke', 'Authorization revoked'),
                ])),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=oauth2_settings.APPLICATION_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(fields=('application', 'token_family'), name='client_login_app_family_uniq'),
                    models.CheckConstraint(condition=(models.Q(revoked_at__isnull=True, revoke_reason='') |
                        (models.Q(revoked_at__isnull=False) & ~models.Q(revoke_reason=''))), name='client_login_revoke_pair'),
                ],
            },
        ),
    ]
