from django.db import migrations


def set_builtin_device_platform_types(apps, schema_editor):
    platform_model = apps.get_model('assets', 'Platform')
    platforms = platform_model.objects.using(schema_editor.connection.alias).filter(
        category='device', internal=True, type='general',
    )
    for name, platform_type in (('Cisco', 'cisco'), ('Huawei', 'huawei'), ('H3C', 'h3c')):
        platforms.filter(name=name).update(type=platform_type)


class Migration(migrations.Migration):
    dependencies = [('assets', '0033_workflow_foundation')]
    operations = [
        migrations.RunPython(set_builtin_device_platform_types, migrations.RunPython.noop),
    ]
