from django.utils.translation import gettext_lazy as _

from orgs.models import Organization
from .base import BaseType

CHATX_NAME = 'ChatX'


class GPTTypes(BaseType):
    CHATGPT = 'chatgpt', _('ChatGPT')

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
        constrains = {
            '*': {
                'ansible_enabled': False,
                'ping_enabled': False,
                'gather_facts_enabled': False,
                'verify_account_enabled': False,
                'change_secret_enabled': False,
                'push_account_enabled': False,
                'gather_accounts_enabled': False,
            }
        }
        return constrains

    @classmethod
    def _get_protocol_constrains(cls) -> dict:
        return {
            '*': {
                'choices': '__self__',
            }
        }

    @classmethod
    def internal_platforms(cls):
        return {
            cls.CHATGPT: [
                {'name': 'ChatGPT'}
            ],
        }

    @classmethod
    def get_community_types(cls):
        return [
            cls.CHATGPT,
        ]


def create_or_update_chatx_resources(chatx_name=CHATX_NAME, org_id=Organization.SYSTEM_ID):
    from django.apps import apps

    platform_model = apps.get_model('assets', 'Platform')
    asset_model = apps.get_model('assets', 'Asset')
    account_model = apps.get_model('accounts', 'Account')

    platform, _ = platform_model.objects.update_or_create(
        name=chatx_name,
        defaults={
            'internal': True,
            'type': chatx_name,
            'category': 'ai',
        }
    )
    asset, __ = asset_model.objects.update_or_create(
        address=chatx_name,
        defaults={
            'name': chatx_name,
            'platform': platform,
            'org_id': org_id
        }
    )

    account, __ = account_model.objects.update_or_create(
        username=chatx_name,
        defaults={
            'name': chatx_name,
            'asset': asset,
            'org_id': org_id
        }
    )
    return account
