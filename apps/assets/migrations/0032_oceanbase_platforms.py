from django.db import migrations


def create_oceanbase_platforms(apps, schema_editor):
    platform_model = apps.get_model('assets', 'Platform')
    automation_model = apps.get_model('assets', 'PlatformAutomation')
    protocol_model = apps.get_model('assets', 'PlatformProtocol')
    db = schema_editor.connection.alias

    for mode, name in (('mysql', 'OceanBase-MySQL'), ('oracle', 'OceanBase-Oracle')):
        platform, created = platform_model.objects.using(db).get_or_create(
            name=name,
            defaults={
                'category': 'database',
                'type': 'oceanbase',
                'internal': True,
                'charset': 'utf-8',
                'gateway_enabled': True,
                'su_enabled': False,
            },
        )
        if not created:
            if platform.category != 'database' or platform.type != 'oceanbase':
                raise ValueError(f'Platform name {name} is already used by another type')
            continue
        automation_model.objects.using(db).create(platform=platform)
        protocol_model.objects.using(db).create(
            platform=platform,
            name='mysql',
            port=2881,
            primary=True,
            required=True,
            default=True,
            public=True,
            setting={'tenant_mode': mode},
        )


class Migration(migrations.Migration):
    dependencies = [('assets', '0031_winrm_terminal_access')]
    operations = [migrations.RunPython(create_oceanbase_platforms, migrations.RunPython.noop)]
