from django.utils.translation import gettext_lazy as _

from .base import BaseType


class WebTypes(BaseType):
    WEBSITE = 'website', _('Website')

    @classmethod
    def _get_base_constrains(cls) -> dict:
        return {
            '*': {
                'charset_enabled': False,
                'gateway_enabled': False,
                'su_enabled': False,
            }
        }

    @classmethod
    def _get_automation_constrains(cls) -> dict:
        disabled = {
            'ansible_enabled': False,
            'ping_enabled': False,
            'gather_facts_enabled': False,
            'verify_account_enabled': False,
            'change_secret_enabled': False,
            'push_account_enabled': False,
            'gather_accounts_enabled': False,
            'remove_account_enabled': False,
        }
        return {
            '*': disabled,
            cls.WEBSITE: {
                'ansible_enabled': True,
                'ping_enabled': True,
                'gather_facts_enabled': True,
                'verify_account_enabled': True,
                'change_secret_enabled': True,
                'push_account_enabled': True,
                'gather_accounts_enabled': True,
                'remove_account_enabled': True,
            },
        }

    @classmethod
    def _get_protocol_constrains(cls) -> dict:
        return {
            '*': {
                'choices': ['http'],
            }
        }

    @classmethod
    def internal_platforms(cls):
        return {
            cls.WEBSITE: [
                {'name': 'Website'},
            ],
        }

    @classmethod
    def get_community_types(cls):
        return [
            cls.WEBSITE,
        ]
