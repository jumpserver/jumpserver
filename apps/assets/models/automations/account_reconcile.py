from django.utils.translation import ugettext_lazy as _

from ops.const import StrategyChoice
from .base import BaseAutomation


class ReconcileAutomation(BaseAutomation):
    class Meta:
        verbose_name = _("Reconcile strategy")

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'type': StrategyChoice.push
        })
        return attr_json
