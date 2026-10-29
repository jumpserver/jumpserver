from django.db import migrations, models
from django.utils import timezone


def expire_sessions_without_deadline(apps, schema_editor):
    # The previous implementation did not record the configured login deadline.
    # Reauthentication establishes it without guessing from rotated credentials.
    Session = apps.get_model('authentication', 'ClientLoginSession')
    Session.objects.using(schema_editor.connection.alias).filter(revoked_at__isnull=True).update(
        revoked_at=timezone.now(), revoke_reason='policy_changed',
    )


class Migration(migrations.Migration):
    dependencies = [('authentication', '0015_connectiontoken_client_login_session')]

    operations = [
        migrations.AddField(
            model_name='clientloginsession', name='expires_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(expire_sessions_without_deadline, migrations.RunPython.noop),
    ]
