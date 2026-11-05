from django.db import migrations


def enable_winrm_terminal(apps, schema_editor):
    # WinRM was always forced private while it only served automation jobs.
    apps.get_model('assets', 'PlatformProtocol').objects.using(schema_editor.connection.alias).filter(
        name='winrm', public=False,
    ).update(public=True)


class Migration(migrations.Migration):
    dependencies = [('assets', '0030_zone_cidrs_auto_assign')]
    operations = [migrations.RunPython(enable_winrm_terminal, migrations.RunPython.noop)]
