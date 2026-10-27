from django.db import migrations, models
from django.db.models import Exists, OuterRef, Q


def validate_rollback(apps, schema_editor):
    Record = apps.get_model('accounts', 'PushSecretRecord')
    records = Record.objects.using(schema_editor.connection.alias)
    newer = records.filter(account_id=OuterRef('account_id'), is_first_login=True).filter(
        Q(date_created__gt=OuterRef('date_created'))
        | Q(date_created=OuterRef('date_created'), id__gt=OuterRef('id')),
    )
    unfinished = records.filter(is_first_login=True, account__isnull=False).filter(~Exists(newer)).exclude(
        status='success', execution__status='success', execution__date_finished__isnull=False,
    )
    if unfinished.exists():
        raise ValueError('Unprepared same-name accounts exist; finish or remove them before rolling back account preparation.')


class Migration(migrations.Migration):
    dependencies = [('accounts', '0012_account_follow_template')]

    operations = [
        migrations.AddField(
            model_name='pushsecretrecord', name='is_first_login',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(migrations.RunPython.noop, validate_rollback),
    ]
