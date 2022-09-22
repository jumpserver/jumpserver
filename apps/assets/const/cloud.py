from .base import BaseType


class CloudTypes(BaseType):
    PUBLIC = 'public', 'Public cloud'
    PRIVATE = 'private', 'Private cloud'
    K8S = 'k8s', 'Kubernetes'

    @classmethod
    def _get_base_constrains(cls) -> dict:
        return {
            '*': {
                'charset_enabled': False,
                'domain_enabled': False,
                'su_enabled': False,
            }
        }

    @classmethod
    def _get_automation_constrains(cls) -> dict:
        constrains = {
            '*': {
                'gather_facts_enabled': False,
                'verify_account_enabled': False,
                'change_password_enabled': False,
                'create_account_enabled': False,
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
