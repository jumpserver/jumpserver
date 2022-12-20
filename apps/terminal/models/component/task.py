from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.db.models import JMSBaseModel
from .terminal import Terminal


class Task(JMSBaseModel):
    NAME_CHOICES = (
        ("kill_session", "Kill Session"),
    )

    name = models.CharField(max_length=128, choices=NAME_CHOICES, verbose_name=_("Name"))
    args = models.CharField(max_length=1024, verbose_name=_("Args"))
    kwargs = models.JSONField(default=dict, verbose_name=_("Kwargs"))
    terminal = models.ForeignKey(Terminal, null=True, on_delete=models.SET_NULL)
    is_finished = models.BooleanField(default=False)
    date_finished = models.DateTimeField(null=True)

    class Meta:
        db_table = "terminal_task"
        verbose_name = _("Task")
