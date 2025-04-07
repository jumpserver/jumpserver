from django.utils.translation import gettext_lazy as _

from .base import BaseType


class DirectoryTypes(BaseType):
    GENERAL = 'general', _('General')
    # LDAP = 'ldap', _('LDAP')
    # AD = 'ad', _('Active Directory')
    WINDOWS_AD = 'windows_ad', _('Windows Active Directory')

    # AZURE_AD = 'azure_ad', _('Azure Active Directory')

    @classmethod
    def _get_base_constrains(cls) -> dict:
        return {
            '*': {
                'charset_enabled': False,
                'domain_enabled': True,
                'ds_enabled': False,
                'su_enabled': True,
            }
        }

    @classmethod
    def _get_automation_constrains(cls) -> dict:
        constrains = {
            '*': {
                'ansible_enabled': False,
            },
            cls.WINDOWS_AD: {
                'ansible_enabled': True,
                'ping_enabled': True,
                'gather_facts_enabled': False,
                'verify_account_enabled': True,
                'change_secret_enabled': True,
                'push_account_enabled': True,
                'gather_accounts_enabled': True,
            }
        }
        return constrains

    @classmethod
    def _get_protocol_constrains(cls) -> dict:
        return {
            cls.GENERAL: {
                'choices': ['ssh']
            },
            cls.WINDOWS_AD: {
                'choices': ['rdp', 'ssh', 'vnc', 'winrm']
            },
        }

    @classmethod
    def internal_platforms(cls):
        return {
            cls.WINDOWS_AD: [
                {'name': 'Windows Active Directory'}
            ],
        }

    @classmethod
    def get_community_types(cls):
        return [
            cls.GENERAL,
        ]
