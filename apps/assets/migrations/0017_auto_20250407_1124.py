# Generated by Django 4.1.13 on 2025-04-07 03:24

import json

from django.db import migrations

from assets.const import AllTypes


def add_ds_platforms(apps, schema_editor):
    data = """
[
    {
        "created_by": "system",
        "updated_by": "system",
        "comment": "",
        "name": "Windows active directory",
        "category": "ds",
        "type": "windows_ad",
        "meta": {},
        "internal": true,
        "domain_enabled": true,
        "su_enabled": false,
        "su_method": null,
        "custom_fields": [],
        "automation": {
            "ansible_enabled": true,
            "ansible_config": {
                "ansible_shell_type": "cmd",
                "ansible_connection": "ssh"
            },
            "ping_enabled": true,
            "ping_method": "ping_by_rdp",
            "ping_params": {},
            "gather_facts_enabled": true,
            "gather_facts_method": "gather_facts_windows",
            "gather_facts_params": {},
            "change_secret_enabled": true,
            "change_secret_method": "change_secret_ad_windows",
            "change_secret_params": {
            },
            "push_account_enabled": true,
            "push_account_method": "push_account_ad_windows",
            "push_account_params": {},
            "verify_account_enabled": true,
            "verify_account_method": "verify_account_by_rdp",
            "verify_account_params": {

            },
            "gather_accounts_enabled": true,
            "gather_accounts_method": "gather_accounts_windows",
            "gather_accounts_params": {

            },
            "remove_account_enabled": true,
            "remove_account_method": "remove_account_ad_windows",
            "remove_account_params": {

            }
        },
        "protocols": [
            {
                "name": "rdp",
                "port": 3389,
                "primary": true,
                "required": false,
                "default": false,
                "public": true,
                "setting": {
                    "console": false,
                    "security": "any"
                }
            },
            {
                "name": "ssh",
                "port": 22,
                "primary": false,
                "required": false,
                "default": false,
                "public": true,
                "setting": {
                    "sftp_enabled": true,
                    "sftp_home": "/tmp"
                }
            },
            {
                "name": "vnc",
                "port": 5900,
                "primary": false,
                "required": false,
                "default": false,
                "public": true,
                "setting": {

                }
            },
            {
                "name": "winrm",
                "port": 5985,
                "primary": false,
                "required": false,
                "default": false,
                "public": false,
                "setting": {
                    "use_ssl": false
                }
            }
        ]
    },
    {
        "created_by": "system",
        "updated_by": "system",
        "comment": "",
        "name": "General",
        "category": "ds",
        "type": "general",
        "meta": {

        },
        "internal": true,
        "domain_enabled": false,
        "su_enabled": false,
        "su_method": null,
        "custom_fields": [

        ],
        "automation": {
            "ansible_enabled": false,
            "ansible_config": {

            }
        },
        "protocols": [
            {
                "name": "ssh",
                "port": 22,
                "primary": true,
                "required": false,
                "default": false,
                "public": true,
                "setting": {
                    "sftp_enabled": true,
                    "sftp_home": "/tmp"
                }
            }
        ]
    }
]
    """
    platform_model = apps.get_model('assets', 'Platform')
    automation_cls = apps.get_model('assets', 'PlatformAutomation')
    platform_datas = json.loads(data)

    for platform_data in platform_datas:
        AllTypes.create_or_update_by_platform_data(
            platform_data, platform_cls=platform_model,
            automation_cls=automation_cls
        )


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0016_directory_service"),
    ]

    operations = [
        migrations.RunPython(add_ds_platforms)
    ]
