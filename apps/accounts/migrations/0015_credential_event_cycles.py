from django.db import migrations, models
from django.db.models import F


def associate_existing_events(apps, schema_editor):
    events = apps.get_model('accounts', 'CredentialRotationEvent').objects.using(
        schema_editor.connection.alias,
    )
    events.filter(rotation_id__isnull=False).update(cycle_id=F('rotation_id'))
    # Old subscription events have no operation identifier. Keep them separate
    # rather than inventing a cycle from a date or an account revision.
    events.filter(rotation_id__isnull=True).update(cycle_id=F('source_event_id'))


class Migration(migrations.Migration):
    dependencies = [('accounts', '0014_applicationcredential_subscription_accounts')]

    operations = [
        migrations.AddField(
            model_name='applicationaudit', name='operation_id',
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.AddField(
            model_name='credentialrotationevent', name='cycle_id',
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.RunPython(associate_existing_events, migrations.RunPython.noop),
    ]
