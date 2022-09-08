from django.utils.translation import ugettext_lazy as _

from ops.const import StrategyChoice
from .common import AutomationStrategy


class VerifyStrategy(AutomationStrategy):
    class Meta:
        verbose_name = _("Verify strategy")

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'type': StrategyChoice.verify
        })
        return attr_json
