# Generated by Django 2.2.5 on 2019-11-25 01:31

from django.db import migrations


def get_storage_data(s):
    from common.utils import get_signer
    import json
    signer = get_signer()
    value = s.value
    encrypted = s.encrypted
    if encrypted:
        value = signer.unsign(value)
    try:
        value = json.loads(value)
    except:
        value = {}
    return value


def get_setting(apps, schema_editor, key):
    model = apps.get_model('settings', 'Setting')
    db_alias = schema_editor.connection.alias
    setting = model.objects.using(db_alias).filter(name=key)
    if not setting:
        return
    return setting[0]


def init_storage_data(model):
    model.objects.update_or_create(
        name='no', type='no',
        defaults={'name': 'no', 'type': 'no'}
    )
    model.objects.update_or_create(
        name='default', type='server',
        defaults={'name': 'default', 'type': 'server'}
    )


def migrate_command_storage(apps, schema_editor):
    model = apps.get_model("terminal", "CommandStorage")
    init_storage_data(model)

    setting = get_setting(apps, schema_editor, "TERMINAL_COMMAND_STORAGE")
    if not setting:
        return
    values = get_storage_data(setting)
    for name, meta in values.items():
        tp = meta.pop("TYPE")
        if not tp or name in ['default', 'no']:
            continue
        model.objects.create(name=name, type=tp, meta=meta)


def migrate_replay_storage(apps, schema_editor):
    model = apps.get_model("terminal", "ReplayStorage")
    init_storage_data(model)

    setting = get_setting(apps, schema_editor, "TERMINAL_REPLAY_STORAGE")
    if not setting:
        return
    values = get_storage_data(setting)
    for name, meta in values.items():
        tp = meta.pop("TYPE", None)
        if not tp or name in ['default', 'no']:
            continue
        model.objects.create(name=name, type=tp, meta=meta)


class Migration(migrations.Migration):

    dependencies = [
        ('terminal', '0016_commandstorage_replaystorage'),
    ]

    operations = [
        migrations.RunPython(migrate_command_storage),
        migrations.RunPython(migrate_replay_storage),
    ]
