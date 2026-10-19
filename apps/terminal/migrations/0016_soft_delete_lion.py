from django.db import migrations


def soft_delete_lion_terminals(apps, schema_editor):
    terminal_model = apps.get_model('terminal', 'Terminal')
    db_alias = schema_editor.connection.alias
    terminal_model.objects.using(db_alias).filter(
        type='lion', is_deleted=False,
    ).update(is_deleted=True)


class Migration(migrations.Migration):
    dependencies = [
        ('terminal', '0015_sessionjoinrecord_joiner_display_and_more'),
    ]

    operations = [
        # Rolling back must not restore terminals deleted before this migration.
        migrations.RunPython(soft_delete_lion_terminals, migrations.RunPython.noop),
    ]
