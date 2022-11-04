import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger


logger = get_logger(__name__)


class Status(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    session_online = models.IntegerField(verbose_name=_("Session Online"), default=0)
    cpu_load = models.FloatField(verbose_name=_("CPU Load"), default=0)
    memory_used = models.FloatField(verbose_name=_("Memory Used"))
    disk_used = models.FloatField(verbose_name=_("Disk Used"), default=0)
    connections = models.IntegerField(verbose_name=_("Connections"), default=0)
    threads = models.IntegerField(verbose_name=_("Threads"), default=0)
    boot_time = models.FloatField(verbose_name=_("Boot Time"), default=0)
    terminal = models.ForeignKey('terminal.Terminal', null=True, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'terminal_status'
        get_latest_by = 'date_created'
        verbose_name = _("Status")


