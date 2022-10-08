import os.path
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings

from orgs.mixins.models import JMSOrgBaseModel
from ..ansible.inventory import JMSInventory
from ..mixin import PeriodTaskModelMixin


class BaseAnsibleTask(PeriodTaskModelMixin, JMSOrgBaseModel):
    owner = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    assets = models.ManyToManyField('assets.Asset', verbose_name=_("Assets"))
    account = models.CharField(max_length=128, default='root', verbose_name=_('Account'))
    account_policy = models.CharField(max_length=128, default='root', verbose_name=_('Account policy'))
    last_execution = models.ForeignKey('BaseAnsibleExecution', verbose_name=_("Last execution"), on_delete=models.SET_NULL, null=True)
    date_last_run = models.DateTimeField(null=True, verbose_name=_('Date last run'))

    class Meta:
        abstract = True

    @property
    def inventory(self):
        inv = JMSInventory(self.assets.all(), self.account, self.account_policy)
        return inv.generate()

    def get_register_task(self):
        raise NotImplemented

    def to_json(self):
        raise NotImplemented


class BaseAnsibleExecution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    status = models.CharField(max_length=16, verbose_name=_('Status'), default='running')
    task = models.ForeignKey(BaseAnsibleTask, on_delete=models.CASCADE, null=True)
    result = models.JSONField(blank=True, null=True, verbose_name=_('Result'))
    summary = models.JSONField(default=dict, verbose_name=_('Summary'))
    creator = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    date_start = models.DateTimeField(null=True, verbose_name=_('Date start'), db_index=True)
    date_finished = models.DateTimeField(null=True)

    class Meta:
        abstract = True
        ordering = ["-date_start"]

    def __str__(self):
        return str(self.id)

    def private_dir(self):
        uniq = self.date_created.strftime('%Y%m%d_%H%M%S') + '_' + self.short_id
        return os.path.join(settings.ANSIBLE_DIR, self.task.name, uniq)

    def get_runner(self):
        raise NotImplemented

    def update_task(self):
        self.task.last_execution = self
        self.task.date_last_run = timezone.now()
        self.task.save(update_fields=['last_execution', 'date_last_run'])

    def start(self, **kwargs):
        runner = self.get_runner()
        try:
            cb = runner.run(**kwargs)
            self.status = cb.status
            self.summary = cb.summary
            self.result = cb.result
            self.date_finished = timezone.now()
        except Exception as e:
            self.status = 'failed'
            self.summary = {'error': str(e)}
        finally:
            self.save()
            self.update_task()

    @property
    def is_finished(self):
        return self.status in ['succeeded', 'failed']

    @property
    def is_success(self):
        return self.status == 'succeeded'

    @property
    def time_cost(self):
        if self.date_finished and self.date_start:
            return (self.date_finished - self.date_start).total_seconds()
        return None

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def timedelta(self):
        if self.date_start and self.date_finished:
            return self.date_finished - self.date_start
        return None


