from django.db import migrations


def migrate_windows_rdp_verify_methods(apps, schema_editor):
    automation_model = apps.get_model('assets', 'PlatformAutomation')
    automation_model.objects.filter(
        change_secret_method='change_secret_windows_rdp_verify'
    ).update(change_secret_method='change_secret_local_windows')
    automation_model.objects.filter(
        push_account_method='push_account_windows_rdp_verify'
    ).update(push_account_method='push_account_local_windows')


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0023_platformpackage_platform_package'),
    ]

    operations = [
        migrations.RunPython(
            migrate_windows_rdp_verify_methods,
            migrations.RunPython.noop,
        ),
    ]
