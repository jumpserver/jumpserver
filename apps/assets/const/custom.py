from .base import BaseType


class CustomTypes(BaseType):
    @classmethod
    def get_choices(cls):
        types = cls.get_custom_platforms().values_list('type', flat=True).distinct()
        return [(t, t) for t in types]

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
    def _get_protocol_constrains(cls) -> dict:
        constrains = {}
        for platform in cls.get_custom_platforms():
            choices = list(platform.protocols.values_list('name', flat=True))
            if platform.type in constrains:
                choices = constrains[platform.type]['choices'] + choices
            constrains[platform.type] = {'choices': choices}
        return constrains

    @classmethod
    def internal_platforms(cls):
        return {
            # cls.PUBLIC: [],
            # cls.PRIVATE: [{'name': 'Vmware-vSphere'}],
            # cls.K8S: [{'name': 'Kubernetes'}],
        }

    @classmethod
    def get_custom_platforms(cls):
        from assets.models import Platform
        return Platform.objects.filter(category='custom')
