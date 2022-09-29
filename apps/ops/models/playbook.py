from django.db import models
from django.utils.translation import gettext_lazy as _

from orgs.mixins.models import JMSOrgBaseModel
from ..mixin import PeriodTaskModelMixin


class PlaybookTask(PeriodTaskModelMixin, JMSOrgBaseModel):
    assets = models.ManyToManyField('assets.Asset', verbose_name=_("Assets"))
    account = models.CharField(max_length=128, default='root', verbose_name=_('Account'))
    playbook = models.FilePathField(max_length=1024, verbose_name=_("Playbook"))
    owner = models.CharField(max_length=1024, verbose_name=_("Owner"))
    comment = models.TextField(blank=True, verbose_name=_("Comment"))

    def get_register_task(self):
        pass
