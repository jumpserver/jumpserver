from collections import defaultdict

from common.decorators import cached_method
from .base import BaseType


class CustomTypes(BaseType):
    @classmethod
    def get_choices(cls):
        try:
            platforms = list(cls.get_custom_platforms())
        except Exception:
            return []
        types = set([p.type for p in platforms])
        choices = [(t, t) for t in types]
        return choices

    @classmethod
    def _get_base_constrains(cls) -> dict:
        return {
            '*': {
                'charset_enabled': False,
                'domain_enabled': False,
                'su_enabled': False,
            },
        }

    @classmethod
    def _get_automation_constrains(cls) -> dict:
        constrains = {
            '*': {
                'ansible_enabled': False,
                'ansible_config': {},
                'gather_facts_enabled': False,
                'verify_account_enabled': False,
                'change_secret_enabled': False,
                'push_account_enabled': False,
                'gather_accounts_enabled': False,
            }
        }
        return constrains

    @classmethod
    @cached_method(5)
    def _get_protocol_constrains(cls) -> dict:
        from assets.models import PlatformProtocol
        _constrains = defaultdict(set)
        protocols = PlatformProtocol.objects \
            .filter(platform__category='custom') \
            .values_list('name', 'platform__type')
        for name, tp in protocols:
            _constrains[tp].add(name)

        constrains = {
            tp: {'choices': list(choices)}
            for tp, choices in _constrains.items()
        }
        return constrains

    @classmethod
    def internal_platforms(cls):
        return {}

    @classmethod
    @cached_method(5)
    def get_custom_platforms(cls):
        from assets.models import Platform
        platforms = Platform.objects.filter(category='custom')
        return platforms
