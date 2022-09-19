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
                'domain_enabled': True,
                'su_enabled': True,
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
