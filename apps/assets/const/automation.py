from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _


class Connectivity(TextChoices):
    UNKNOWN = 'unknown', _('Unknown')
    OK = 'ok', _('Ok')
    FAILED = 'failed', _('Failed')


class AutomationTypes(TextChoices):
    ping = 'ping', _('Ping')
    ping_gateway = 'ping_gateway', _('Ping gateway')
    gather_facts = 'gather_facts', _('Gather facts')

    @classmethod
    def get_type_model(cls, tp):
        from assets.models import (
            PingAutomation, GatherFactsAutomation,
        )
        type_model_dict = {
            cls.ping: PingAutomation,
            cls.gather_facts: GatherFactsAutomation,
        }
        return type_model_dict.get(tp)
