from django.utils.translation import ugettext_lazy as _

from ops.const import StrategyChoice
from ops.ansible.runner import PlaybookRunner
from .base import BaseAutomation


class DiscoveryAutomation(BaseAutomation):
    class Meta:
        verbose_name = _("Discovery strategy")

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'type': StrategyChoice.collect
        })
        return attr_json
