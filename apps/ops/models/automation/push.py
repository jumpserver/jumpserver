from django.utils.translation import ugettext_lazy as _

from ops.const import StrategyChoice
from .common import AutomationStrategy


class PushStrategy(AutomationStrategy):
    class Meta:
        verbose_name = _("Push strategy")

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'type': StrategyChoice.push
        })
        return attr_json
