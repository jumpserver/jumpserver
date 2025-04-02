from django.utils.translation import gettext_lazy as _

from .base import BaseType


class ADTypes(BaseType):
    AD = 'ad', _('Active Directory')
    WINDOWS_AD = 'windows_ad', _('Windows Active Directory')
    LDAP = 'ldap', _('LDAP')
    AZURE_AD = 'azure_ad', _('Azure Active Directory')

    @classmethod
    def _get_base_constrains(cls) -> dict:
        return {
            '*': {
                'charset_enabled': False,
                'domain_enabled': True,
                'ad_enabled': False,
                'su_enabled': True,
            }
        }

    @classmethod
    def _get_automation_constrains(cls) -> dict:
        constrains = {
            '*': {
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
            cls.WINDOWS_AD: {
                'choices': ['rdp', 'ssh', 'vnc', 'winrm']
            },
            cls.LDAP: {
                'choices': ['ssh', 'ldap']
            },
            cls.AZURE_AD: {
                'choices': ['ldap']
            }
        }

    @classmethod
    def internal_platforms(cls):
        return {
            cls.AD: [
                {'name': 'Active Directory'}
            ],
            cls.WINDOWS_AD: [
                {'name': 'Windows Active Directory'}
            ],
            cls.LDAP: [
                {'name': 'LDAP'}
            ],
            cls.AZURE_AD: [
                {'name': 'Azure Active Directory'}
            ],
        }

    @classmethod
    def get_community_types(cls):
        return [
            cls.LDAP,
        ]
