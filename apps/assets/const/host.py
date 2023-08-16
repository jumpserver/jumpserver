from django.utils.translation import gettext_lazy as _

from .base import BaseType

GATEWAY_NAME = 'Gateway'


class HostTypes(BaseType):
    LINUX = 'linux', 'Linux'
    WINDOWS = 'windows', 'Windows'
    UNIX = 'unix', 'Unix'
    OTHER_HOST = 'other', _("Other")

    @classmethod
    def _get_base_constrains(cls) -> dict:
        return {
            '*': {
                'charset_enabled': True,
                'charset': 'utf-8',  # default
                'domain_enabled': True,
                'su_enabled': True,
                'su_methods': ['sudo', 'su'],
            },
            cls.WINDOWS: {
                'su_enabled': False,
            },
            cls.OTHER_HOST: {
                'su_enabled': False,
            }
        }

    @classmethod
    def _get_protocol_constrains(cls) -> dict:
        return {
            '*': {
                'choices': ['ssh', 'sftp', 'telnet', 'vnc', 'rdp']
            },
            cls.WINDOWS: {
                'choices': ['rdp', 'ssh', 'sftp', 'vnc', 'winrm']
            }
        }

    @classmethod
    def _get_automation_constrains(cls) -> dict:
        return {
            '*': {
                'ansible_enabled': True,
                'ansible_config': {
                    'ansible_connection': 'smart',
                },
                'ping_enabled': True,
                'gather_facts_enabled': True,
                'gather_accounts_enabled': True,
                'verify_account_enabled': True,
                'change_secret_enabled': True,
                'push_account_enabled': True
            },
            cls.WINDOWS: {
                'ansible_config': {
                    'ansible_shell_type': 'cmd',
                    'ansible_connection': 'smart',
                },
            },
            cls.OTHER_HOST: {
                'ansible_enabled': False,
                'ping_enabled': False,
                'gather_facts_enabled': False,
                'gather_accounts_enabled': False,
                'verify_account_enabled': False,
                'change_secret_enabled': False,
                'push_account_enabled': False
            },
        }

    @classmethod
    def internal_platforms(cls):
        return {
            cls.LINUX: [
                {'name': 'Linux'},
                {
                    'name': GATEWAY_NAME,
                    'domain_enabled': True,
                }
            ],
            cls.UNIX: [
                {'name': 'Unix'},
                {'name': 'macOS'},
                {'name': 'BSD'},
                {
                    'name': 'AIX',
                    'automation': {
                        'push_account_method': 'push_account_aix',
                        'change_secret_method': 'change_secret_aix',
                    }
                },
            ],
            cls.WINDOWS: [
                {'name': 'Windows'},
                {
                    'name': 'Windows-TLS',
                    'protocols_setting': {
                        'rdp': {'security': 'tls'},
                    }
                },
                {
                    'name': 'Windows-RDP',
                    'protocols_setting': {
                        'rdp': {'security': 'rdp'},
                    }
                },
                {
                    'name': 'RemoteAppHost',
                    '_protocols': ['rdp', 'ssh'],
                    'protocols_setting': {
                        'ssh': {
                            'required': True
                        }
                    }
                }
            ]
        }

    @classmethod
    def get_community_types(cls) -> list:
        return [
            cls.LINUX, cls.UNIX, cls.WINDOWS, cls.OTHER_HOST
        ]
