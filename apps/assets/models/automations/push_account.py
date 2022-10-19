from django.utils.translation import ugettext_lazy as _

from .base import BaseAutomation


class PushAccountAutomation(BaseAutomation):
    class Meta:
        verbose_name = _("Push automation")

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'type': 'push_account'
        })
        return attr_json
