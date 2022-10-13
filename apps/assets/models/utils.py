#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from common.utils import validate_ssh_private_key


__all__ = [
    'private_key_validator',
]


def private_key_validator(value):
    if not validate_ssh_private_key(value):
        raise ValidationError(
            _('%(value)s is not an even number'),
            params={'value': value},
        )


def update_internal_platforms(platform_model):
    from assets.const import AllTypes

    platforms = [
        {'name': 'Linux', 'category': 'host', 'type': 'linux'},
        {'name': 'BSD', 'category': 'host', 'type': 'unix'},
        {'name': 'Unix', 'category': 'host', 'type': 'unix'},
        {'name': 'MacOS', 'category': 'host', 'type': 'unix'},
        {'name': 'Windows', 'category': 'host', 'type': 'unix'},
        {
            'name': 'AIX', 'category': 'host', 'type': 'unix',
            'create_account_method': 'create_account_aix',
            'change_secret_method': 'change_secret_aix',
        },
        {'name': 'Windows', 'category': 'host', 'type': 'windows'},
        {
            'name': 'Windows-TLS', 'category': 'host', 'type': 'windows',
            'protocols': [
                {'name': 'rdp', 'port': 3389, 'setting': {'security': 'tls'}},
                {'name': 'ssh', 'port': 22},
            ]
        },
        {
            'name': 'Windows-RDP', 'category': 'host', 'type': 'windows',
            'protocols': [
                {'name': 'rdp', 'port': 3389, 'setting': {'security': 'rdp'}},
                {'name': 'ssh', 'port': 22},
            ]
        },
        # 数据库
        {'name': 'MySQL', 'category': 'database', 'type': 'mysql'},
        {'name': 'PostgreSQL', 'category': 'database', 'type': 'postgresql'},
        {'name': 'Oracle', 'category': 'database', 'type': 'oracle'},
        {'name': 'SQLServer', 'category': 'database', 'type': 'sqlserver'},
        {'name': 'MongoDB', 'category': 'database', 'type': 'mongodb'},
        {'name': 'Redis', 'category': 'database', 'type': 'redis'},

        # 网络设备
        {'name': 'Generic', 'category': 'device', 'type': 'general'},
        {'name': 'Huawei', 'category': 'device', 'type': 'general'},
        {'name': 'Cisco', 'category': 'device', 'type': 'general'},
        {'name': 'H3C', 'category': 'device', 'type': 'general'},

        # Web
        {'name': 'Website', 'category': 'web', 'type': 'general'},

        # Cloud
        {'name': 'Kubernetes', 'category': 'cloud', 'type': 'k8s'},
        {'name': 'VMware vSphere', 'category': 'cloud', 'type': 'private'},
    ]

    platforms = platform_model.objects.all()

    updated = []
    for p in platforms:
        attrs = platform_ops_map.get((p.category, p.type), {})
        if not attrs:
            continue
        for k, v in attrs.items():
            setattr(p, k, v)
        updated.append(p)
    platform_model.objects.bulk_update(updated, list(default_ok.keys()))
