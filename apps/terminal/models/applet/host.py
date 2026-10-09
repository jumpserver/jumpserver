from collections import defaultdict
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from assets.models import Host
from common.db.models import JMSBaseModel
from terminal.const import PublishStatus

__all__ = ['AppletHost', 'AppletHostDeployment']


class AppletHost(Host):
    tinker_version = models.CharField(
        max_length=32, blank=True, default='', editable=False, verbose_name=_('Tinker version'),
    )
    deploy_options = models.JSONField(default=dict, verbose_name=_('Deploy options'))
    auto_create_accounts = models.BooleanField(default=True, verbose_name=_('Auto create accounts'))
    accounts_create_amount = models.IntegerField(default=100, verbose_name=_('Accounts create amount'))
    inited = models.BooleanField(default=False, verbose_name=_('Inited'))
    date_inited = models.DateTimeField(null=True, blank=True, verbose_name=_('Date inited'))
    date_synced = models.DateTimeField(null=True, blank=True, verbose_name=_('Date synced'))
    terminal = models.OneToOneField(
        'terminal.Terminal', on_delete=models.PROTECT, null=True, blank=True,
        related_name='applet_host', verbose_name=_('Terminal')
    )
    using_same_account = models.BooleanField(default=False, verbose_name=_('Using same account'))
    applets = models.ManyToManyField(
        'Applet', verbose_name=_('Applet'),
        through='AppletPublication', through_fields=('host', 'applet'),
    )
    LOCKING_ORG = '00000000-0000-0000-0000-000000000004'

    class Meta:
        verbose_name = _('Hosting')

    def __str__(self):
        return self.name

    @property
    def load(self):
        if not self.terminal:
            return 'offline'
        return self.terminal.load

    def check_terminal_binding(self, request, tinker_version=''):
        request_terminal = getattr(request.user, 'terminal', None)
        if not request_terminal:
            raise ValidationError('Request user has no terminal')
        if request_terminal.type != 'tinker':
            raise ValidationError('Only Tinker terminals can bind an applet host')

        # A service credential must not be able to claim another host at startup.
        if self.terminal_id != request_terminal.pk:
            raise PermissionDenied('Terminal is not bound to this applet host')
        self.date_synced = timezone.now()
        self.tinker_version = tinker_version
        self.save(update_fields=['date_synced', 'tinker_version'])

    def check_applets_state(self, applets_value_list):
        applets = self.applets.all()
        name_version_mapper = {
            value['name']: value['version']
            for value in applets_value_list
        }

        status_applets = defaultdict(list)
        for applet in applets:
            if applet.name not in name_version_mapper:
                status_applets[PublishStatus.failed.value].append(applet)
            elif applet.version != name_version_mapper[applet.name]:
                status_applets[PublishStatus.mismatch.value].append(applet)
            else:
                status_applets[PublishStatus.success.value].append(applet)

        for status, applets in status_applets.items():
            self.publications.filter(applet__in=applets) \
                .exclude(status=status) \
                .update(status=status)

class AppletHostDeployment(JMSBaseModel):
    host = models.ForeignKey('AppletHost', on_delete=models.CASCADE, verbose_name=_('Hosting'))
    initial = models.BooleanField(default=False, verbose_name=_('Initial'))
    status = models.CharField(max_length=16, default='pending', verbose_name=_('Status'))
    date_start = models.DateTimeField(null=True, verbose_name=_('Date start'), db_index=True)
    date_finished = models.DateTimeField(null=True, verbose_name=_("Date finished"))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))
    task = models.UUIDField(null=True, verbose_name=_('Task'))

    class Meta:
        ordering = ('-date_start',)
        verbose_name = _("Applet host deployment")

    def start(self, **kwargs):
        from ...automations.deploy_applet_host import DeployAppletHostManager
        manager = DeployAppletHostManager(self, **kwargs)
        manager.run()

    def install_applet(self, applet_id, **kwargs):
        manager = self.create_deploy_manager(applet_id, **kwargs)
        manager.install_applet(**kwargs)

    def uninstall_applet(self, applet_id, **kwargs):
        manager = self.create_deploy_manager(applet_id, **kwargs)
        manager.uninstall_applet(**kwargs)

    def create_deploy_manager(self, applet_id, **kwargs):
        from ...automations.deploy_applet_host import DeployAppletHostManager
        from .applet import Applet
        if applet_id:
            applet = Applet.objects.get(id=applet_id)
        else:
            applet = None
        return DeployAppletHostManager(self, applet=applet)

    def save_task(self, task):
        self.task = task
        self.save(update_fields=['task'])
