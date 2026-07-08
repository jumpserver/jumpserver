from django.db import models
from django.utils.translation import gettext_lazy as _

from orgs.mixins.models import JMSOrgBaseModel

from .mixins import CREATABLE_REPORT_TYPES

REPORT_VISIBILITY_FILTER_FIELDS = {
    'visible_charts',
    'visible_tables',
}


class Report(JMSOrgBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    tp = models.CharField(max_length=64, verbose_name=_('Type'))
    is_builtin = models.BooleanField(default=False, verbose_name=_('Is builtin'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    days = models.PositiveIntegerField(default=7, verbose_name=_('Range days'))
    filters = models.JSONField(default=dict, verbose_name=_('Filters'))

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('Report')
        ordering = ['-date_created']


def validate_report_payload(tp, filters):
    if tp not in CREATABLE_REPORT_TYPES:
        raise ValueError(f'Unsupported report type: {tp}')
    allowed_keys = REPORT_VISIBILITY_FILTER_FIELDS
    invalid_keys = set((filters or {}).keys()) - allowed_keys
    if invalid_keys:
        raise ValueError(f'Invalid filters: {", ".join(sorted(invalid_keys))}')