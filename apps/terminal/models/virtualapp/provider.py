from django.db import models, transaction
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from accounts.const import SecretType
from common.db.models import JMSBaseModel

__all__ = ['AppProvider', 'AppProviderDeployment']


class AppProvider(JMSBaseModel):
    cache_status_key_prefix = 'virtual_host_{}_status'
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    host = models.OneToOneField(
        'assets.Host', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='app_provider', verbose_name=_('Host'),
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
        return self.host.address if self.host else ''

    def select_gateway(self):
        if not self.host or not self.host.zone:
            return None
        return self.host.zone.select_gateway()

    def bind_terminal(self, terminal):
        if not terminal:
            raise ValidationError('Request user has no terminal')
        if terminal.type != 'panda':
            raise ValidationError('Only Panda terminals can bind an application provider')

        with transaction.atomic():
            provider = self.__class__.objects.select_for_update().get(pk=self.pk)
            if provider.terminal_id and provider.terminal_id != terminal.pk:
                raise ValidationError('Provider is already bound to another terminal')
            terminal = terminal.__class__.objects.select_for_update().get(pk=terminal.pk)
            bound_provider = self.__class__.objects.select_for_update().filter(
                terminal=terminal,
            ).exclude(pk=self.pk).first()
            if bound_provider:
                if bound_provider.host_id:
                    raise ValidationError('Terminal is already bound to another provider')
                bound_provider.delete()

            self.terminal = terminal
            self.save(update_fields=['terminal', 'date_updated'])

    def check_terminal_binding(self, request):
        self.bind_terminal(getattr(request.user, 'terminal', None))

    def select_account(self):
        if not self.host:
            return None
        accounts = self.host.accounts.active().filter(
            secret_type__in=(SecretType.PASSWORD, SecretType.SSH_KEY),
        ).order_by(
            '-privileged', '-date_updated'
        )
        return next((account for account in accounts if account.username and account.secret), None)

    def select_deploy_account(self):
        if not self.host:
            return None
        accounts = self.host.accounts.active().filter(
            models.Q(privileged=True) | models.Q(username='root'),
            secret_type__in=(SecretType.PASSWORD, SecretType.SSH_KEY),
        ).order_by('-date_updated')
        accounts = sorted(accounts, key=lambda account: account.username == 'root', reverse=True)
        return next((account for account in accounts if account.username and account.secret), None)

    @property
    def latest_deployment(self):
        if self._state.adding:
            return None
        return self.deployments.filter(publication__isnull=True).first()

    def validate_deployment(self):
        from terminal.serializers.virtualapp_provider import AppProviderDeployOptionsSerializer
        from terminal.automations.deploy_app_provider import load_manifest

        if not self.host:
            raise ValidationError({'host': _('Provider host is required before deployment')})
        if self.host.platform.type != 'linux':
            raise ValidationError({'host': _('Provider deployment requires a Linux host')})
        ssh = self.host.protocols.filter(name='ssh').first()
        if not ssh or not 1 <= ssh.port <= 65535 or ssh.port == 9001:
            raise ValidationError({'host': _('A valid SSH port different from the Panda API port is required')})
        if not self.select_deploy_account():
            raise ValidationError({
                'host': _('An active root or privileged SSH account with a password or private key is required')
            })
        if self.container_count:
            raise ValidationError({'host': _('Disable the provider and wait for all containers to exit before deployment')})
        try:
            load_manifest()
        except (OSError, ValueError) as exc:
            raise ValidationError({'deploy_options': _('Invalid offline deployment resources: %s') % exc}) from exc
        options = AppProviderDeployOptionsSerializer(data=self.deploy_options)
        if not options.is_valid():
            raise ValidationError({'deploy_options': options.errors})
        if not options.validated_data['PANDA_IMAGE']:
            raise ValidationError({'deploy_options': {
                'PANDA_IMAGE': _('Select a Panda image already loaded on the provider or prepare the Installer offline resources')
            }})
        start, end = map(int, options.validated_data['PANDA_RANGE_PORTS'].split('-'))
        if start <= ssh.port <= end:
            raise ValidationError({'deploy_options': {
                'PANDA_RANGE_PORTS': _('Container port range must not include the SSH port')
            }})
        return options.validated_data

    @property
    def connection_ready(self):
        if not self.host or not self.host.is_active:
            return False
        deployment = self.latest_deployment
        if deployment and deployment.status != 'success':
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
