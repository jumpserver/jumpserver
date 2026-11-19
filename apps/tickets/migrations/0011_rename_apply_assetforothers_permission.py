from django.db import migrations


OLD_CODENAME = 'apply_asset_for_others'
NEW_CODENAME = 'apply_assetforothers'


def rename_permission(apps, schema_editor, old_codename, new_codename):
    Permission = apps.get_model('auth', 'Permission')
    Permission.objects.using(schema_editor.connection.alias).filter(
        content_type__app_label='tickets',
        content_type__model='workflow',
        codename=old_codename,
    ).update(codename=new_codename)


def forwards(apps, schema_editor):
    rename_permission(apps, schema_editor, OLD_CODENAME, NEW_CODENAME)


def backwards(apps, schema_editor):
    rename_permission(apps, schema_editor, NEW_CODENAME, OLD_CODENAME)


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0010_ticket_workflow_refactor'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterModelOptions(
            name='workflow',
            options={
                'default_permissions': ('add', 'change', 'view'),
                'ordering': ['name', 'id'],
                'permissions': [
                    ('apply_assetforothers', 'Apply for asset access on behalf of another user'),
                ],
                'verbose_name': 'Approval workflow',
            },
        ),
    ]
