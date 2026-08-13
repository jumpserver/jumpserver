from django.db import migrations

from assets.const import AllTypes


VIRTUAL_APP_HOST_PLATFORM = {
    'created_by': 'system',
    'updated_by': 'system',
    'comment': '',
    'name': 'VirtualAppHost',
    'category': 'host',
    'type': 'linux',
    'meta': {},
    'internal': True,
    'charset': 'utf-8',
    'gateway_enabled': True,
    'ds_enabled': False,
    'su_enabled': True,
    'su_method': None,
    'custom_fields': [],
    'automation': {
        'ansible_enabled': True,
        'ansible_config': {
            'ansible_connection': 'ssh',
        },
        'ping_enabled': True,
        'ping_method': 'posix_ping',
        'ping_params': {},
        'gather_facts_enabled': True,
        'gather_facts_method': 'gather_facts_posix',
        'gather_facts_params': {},
        'change_secret_enabled': True,
        'change_secret_method': 'change_secret_posix',
        'change_secret_params': {},
        'push_account_enabled': True,
        'push_account_method': 'push_account_posix',
        'push_account_params': {
            'home': '',
            'sudo': '/bin/whoami',
            'shell': '/bin/bash',
            'groups': '',
        },
        'verify_account_enabled': True,
        'verify_account_method': 'verify_account_posix',
        'verify_account_params': {},
        'gather_accounts_enabled': True,
        'gather_accounts_method': 'gather_accounts_posix',
        'gather_accounts_params': {},
        'remove_account_enabled': True,
        'remove_account_method': 'remove_account_posix',
        'remove_account_params': {},
    },
    'protocols': [
        {
            'name': 'ssh',
            'port': 22,
            'primary': True,
            'required': True,
            'default': True,
            'public': True,
            'setting': {
                'sftp_home': '/tmp',
                'sftp_enabled': True,
            },
        },
    ],
}


def add_virtual_app_host_platform(apps, schema_editor):
    platform_model = apps.get_model('assets', 'Platform')
    automation_model = apps.get_model('assets', 'PlatformAutomation')
    AllTypes.create_or_update_by_platform_data(
        VIRTUAL_APP_HOST_PLATFORM.copy(),
        platform_cls=platform_model,
        automation_cls=automation_model,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0023_platformpackage_platform_package'),
    ]

    operations = [
        migrations.RunPython(
            add_virtual_app_host_platform,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
