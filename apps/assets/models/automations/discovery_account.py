from django.utils.translation import ugettext_lazy as _

from .base import BaseAutomation


class DiscoveryAccountAutomation(BaseAutomation):
    class Meta:
        verbose_name = _("Discovery account automation")

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'type': 'discover_account'
        })
        return attr_json
