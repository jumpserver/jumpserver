from django.db import models

from common.db.models import ChoicesMixin


from .category import ConstrainMixin


class CloudTypes(ConstrainMixin, ChoicesMixin, models.TextChoices):
    K8S = 'k8s', 'Kubernetes'

    def category_constrains(self):
        return {
            'domain_enabled': False,
            'su_enabled': False,
            'ping_enabled': False,
            'gather_facts_enabled': False,
            'verify_account_enabled': False,
            'change_password_enabled': False,
            'create_account_enabled': False,
            'gather_accounts_enabled': False,
            '_protocols': []
        }

    @classmethod
    def platform_constraints(cls):
        return {
            cls.K8S: {
                '_protocols': ['k8s']
            }
        }
