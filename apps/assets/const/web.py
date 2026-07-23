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
        constrains = {
            '*': {
                'ansible_enabled': True,
                'ansible_config': {
                    'ansible_connection': 'local',
                },
                'ping_enabled': True,
                'gather_facts_enabled': True,
                'verify_account_enabled': True,
                'change_secret_enabled': True,
                'push_account_enabled': True,
                'gather_accounts_enabled': True,
                'remove_account_enabled': True,
            }
        }
        return constrains

    @classmethod
    def _get_protocol_constrains(cls) -> dict:
        return {
            '*': {
                'choices': ['http'],
            }
        }

    @classmethod
    def get_choices(cls):
        choices = list(super().get_choices())
        try:
            from assets.models import Platform
            dynamic_types = Platform.objects.filter(category='web').values_list('type', flat=True)
        except Exception:
            return choices

        exists = {value for value, _label in choices}
        for tp in dynamic_types:
            if tp in exists:
                continue
            choices.append((tp, tp))
        return choices

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
