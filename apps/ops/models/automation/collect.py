from django.utils.translation import ugettext_lazy as _

from ops.const import StrategyChoice
from .common import AutomationStrategy


class CollectStrategy(AutomationStrategy):
    class Meta:
        verbose_name = _("Collect strategy")

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'type': StrategyChoice.collect
        })
        return attr_json
