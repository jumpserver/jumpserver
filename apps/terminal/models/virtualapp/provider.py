from django.db import models, transaction
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from common.db.models import JMSBaseModel

__all__ = ['AppProvider', 'AppProviderDeployment']


class AppProvider(JMSBaseModel):
    class RuntimeType(models.TextChoices):
        docker = 'docker', 'Docker'
        podman = 'podman', 'Podman'

    class ConnectionMode(models.TextChoices):
        direct = 'direct', _('Direct')
        ssh = 'ssh', 'SSH'

    cache_status_key_prefix = 'virtual_host_{}_status'
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    hostname = models.CharField(max_length=128, verbose_name=_('Hostname'))
    host = models.OneToOneField(
        'assets.Host', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='app_provider', verbose_name=_('Host'),
    )
    runtime_type = models.CharField(
        max_length=16, choices=RuntimeType.choices, default=RuntimeType.docker,
        verbose_name=_('Runtime type'),
    )
    connection_mode = models.CharField(
        max_length=16, choices=ConnectionMode.choices, default=ConnectionMode.direct,
        verbose_name=_('Connection mode'),
    )
    service_url = models.URLField(
        max_length=1024, blank=True, default='', verbose_name=_('Service URL'),
    )
    deploy_options = models.JSONField(default=dict, blank=True, verbose_name=_('Deploy options'))
    terminal = models.OneToOneField(
        'terminal.Terminal', on_delete=models.CASCADE, null=True, blank=True,
        related_name='app_provider', verbose_name=_('Terminal')
    )
    apps = models.ManyToManyField(
        'VirtualApp', verbose_name=_('Virtual app'),
        through='VirtualAppPublication', through_fields=('provider', 'app'),
    )

    class Meta:
        ordering = ('-date_created',)
        verbose_name = _('App Provider')

    @property
    def load(self):
        if not self.terminal:
            return 'offline'
        return self.terminal.load

    @property
    def container_count(self):
        containers = cache.get(self.cache_status_key_prefix.format(self.id), [])
        return len(containers)

    @property
    def address(self):
        return self.host.address if self.host else self.hostname

    def select_gateway(self):
        if not self.host or not self.host.zone:
            return None
        return self.host.zone.select_gateway()

    def bind_terminal(self, terminal):
        if not terminal:
            raise ValidationError('Request user has no terminal')

        with transaction.atomic():
            terminal = terminal.__class__.objects.select_for_update().get(pk=terminal.pk)
            bound_provider = self.__class__.objects.select_for_update().filter(
                terminal=terminal,
            ).exclude(pk=self.pk).first()
            if bound_provider:
                is_legacy_direct = (
                    bound_provider.connection_mode == self.ConnectionMode.direct
                    and bound_provider.host_id is None
                )
                if not is_legacy_direct:
                    raise ValidationError('Terminal is already bound to another provider')
                bound_provider.delete()

            self.terminal = terminal
            self.save(update_fields=['terminal', 'date_updated'])

    def check_terminal_binding(self, request):
        self.bind_terminal(getattr(request.user, 'terminal', None))

    def select_account(self):
        if not self.host:
            return None
        return self.host.accounts.active().order_by(
            '-privileged', '-date_updated'
        ).first()

    @property
    def connection_ready(self):
        if self.connection_mode == self.ConnectionMode.direct:
            return True
        if not self.host:
            return False
        has_ssh = self.host.protocols.filter(name='ssh').exists()
        return has_ssh and self.select_account() is not None


class AppProviderDeployment(JMSBaseModel):
    provider = models.ForeignKey(
        'AppProvider', on_delete=models.CASCADE, related_name='deployments',
        verbose_name=_('App Provider'),
    )
    publication = models.ForeignKey(
        'VirtualAppPublication', on_delete=models.CASCADE, null=True, blank=True,
        related_name='deployments', verbose_name=_('Virtual app publication'),
    )
    status = models.CharField(max_length=16, default='pending', verbose_name=_('Status'))
    date_start = models.DateTimeField(null=True, blank=True, verbose_name=_('Date start'))
    date_finished = models.DateTimeField(null=True, blank=True, verbose_name=_('Date finished'))
    task = models.UUIDField(null=True, blank=True, verbose_name=_('Task'))

    class Meta:
        ordering = ('-date_created',)
        verbose_name = _('App Provider deployment')

    def start(self):
        from terminal.automations.deploy_app_provider import DeployAppProviderManager
        DeployAppProviderManager(self).run()

    def save_task(self, task):
        self.task = task
        self.save(update_fields=['task'])
