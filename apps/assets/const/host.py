from .base import BaseType


class HostTypes(BaseType):
    LINUX = 'linux', 'Linux'
    WINDOWS = 'windows', 'Windows'
    UNIX = 'unix', 'Unix'
    OTHER_HOST = 'other', "Other"

    @classmethod
    def _get_base_constrains(cls) -> dict:
        return {
            '*': {
                'charset_enabled': True,
                'charset': 'utf-8',  # default
                'domain_enabled': True,
                'su_enabled': True,
                'su_methods': [
                    {
                      'name': 'sudo su',
                      'id': 'sudo su'
                    },
                    {
                        'name': 'su -',
                        'id': 'su -'
                    }
                ],
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
               'choices': ['ssh', 'telnet', 'vnc', 'rdp']
            }
        }

    @classmethod
    def _get_automation_constrains(cls) -> dict:
        return {
            '*': {
                'ping_enabled': True,
                'gather_facts_enabled': True,
                'gather_accounts_enabled': True,
                'verify_account_enabled': True,
                'change_password_enabled': True,
                'create_account_enabled': True,
            }
        }

    @classmethod
    def internal_platforms(cls):
        return {
            cls.LINUX: [
                {'name': 'Linux'},
            ],
            cls.UNIX: [
                {'name': 'Unix'},
                {'name': 'macOS'},
                {'name': 'BSD'},
                {'name': 'AIX', 'automation': {
                    'create_account_method': 'create_account_aix',
                    'change_password_method': 'change_password_aix'
                }},
            ],
            cls.WINDOWS: [
                {'name': 'Windows'},
                {'name': 'Windows-TLS', 'protocol_settings': {
                    'rdp': {'security': 'tls'},
                }},
                {'name': 'Windows-RDP', 'protocol_settings': {
                    'rdp': {'security': 'rdp'},
                }}
            ],
            cls.OTHER_HOST: []
        }
