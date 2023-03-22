from django.utils.translation import gettext_lazy as _

from .base import BaseType


class CloudTypes(BaseType):
    PUBLIC = 'public', _('Public cloud')
    PRIVATE = 'private', _('Private cloud')
    K8S = 'k8s', _('Kubernetes')

    @classmethod
    def _get_base_constrains(cls) -> dict:
        return {
            '*': {
                'charset_enabled': False,
                'domain_enabled': False,
                'su_enabled': False,
            },
            cls.K8S: {
                'domain_enabled': True,
            }
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
        return {
            '*': {
                'choices': ['http'],
            },
            cls.K8S: {
                'choices': ['k8s']
            }
        }

    @classmethod
    def internal_platforms(cls):
        return {
            cls.PUBLIC: [],
            cls.PRIVATE: [{'name': 'Vmware-vSphere'}],
            cls.K8S: [{'name': 'Kubernetes'}],
        }

    @classmethod
    def get_community_types(cls):
        return [
            cls.K8S, cls.PUBLIC, cls.PRIVATE
        ]
