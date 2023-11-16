from collections import defaultdict

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from simple_history.utils import bulk_create_with_history

from assets.models import Host
from common.db.models import JMSBaseModel
from common.utils import random_string
from terminal.const import PublishStatus

__all__ = ['AppletHost', 'AppletHostDeployment']


class AppletHost(Host):
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

    def check_terminal_binding(self, request):
        request_terminal = getattr(request.user, 'terminal', None)
        if not request_terminal:
            raise ValidationError('Request user has no terminal')

        self.date_synced = timezone.now()
        if self.terminal == request_terminal:
            self.save(update_fields=['date_synced'])
        else:
            self.terminal = request_terminal
            self.save(update_fields=['terminal', 'date_synced'])

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

    @staticmethod
    def random_username():
        return 'jms_' + random_string(8)

    @staticmethod
    def random_password():
        return random_string(16, special_char=True)

    def generate_accounts(self):
        if not self.auto_create_accounts:
            return
        self.generate_public_accounts()
        self.generate_private_accounts()

    def generate_public_accounts(self):
        now_count = self.accounts.filter(privileged=False, username__startswith='jms').count()
        need = self.accounts_create_amount - now_count

        accounts = []
        account_model = self.accounts.model
        for i in range(need):
            username = self.random_username()
            password = self.random_password()
            account = account_model(
                username=username, secret=password, name=username,
                asset_id=self.id, secret_type='password', version=1,
                org_id=self.LOCKING_ORG, is_active=False,
            )
            accounts.append(account)
        bulk_create_with_history(accounts, account_model, batch_size=20, ignore_conflicts=True)

    def generate_private_accounts_by_usernames(self, usernames):
        accounts = []
        account_model = self.accounts.model
        for username in usernames:
            password = self.random_password()
            username = 'js_' + username
            account = account_model(
                username=username, secret=password, name=username,
                asset_id=self.id, secret_type='password', version=1,
                org_id=self.LOCKING_ORG, is_active=False,
            )
            accounts.append(account)
        bulk_create_with_history(accounts, account_model, batch_size=20, ignore_conflicts=True)

    def generate_private_accounts(self):
        from users.models import User
        usernames = User.objects \
            .filter(is_active=True, is_service_account=False) \
            .exclude(username__startswith='[') \
            .values_list('username', flat=True)
        account_usernames = self.accounts.all().values_list('username', flat=True)
        account_usernames = [username[3:] for username in account_usernames if username.startswith('js_')]
        not_exist_users = set(usernames) - set(account_usernames)
        self.generate_private_accounts_by_usernames(not_exist_users)


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

    def start(self, **kwargs):
        # 重新初始化部署，applet host 关联的终端需要删除
        # 否则 tinker 会因组件注册名称相同，造成冲突，执行任务失败
        if self.host.terminal:
            terminal = self.host.terminal
            self.host.terminal = None
            self.host.save()
            terminal.delete()
        from ...automations.deploy_applet_host import DeployAppletHostManager
        manager = DeployAppletHostManager(self)
        manager.run(**kwargs)

    def install_applet(self, applet_id, **kwargs):
        from ...automations.deploy_applet_host import DeployAppletHostManager
        from .applet import Applet
        if applet_id:
            applet = Applet.objects.get(id=applet_id)
        else:
            applet = None
        manager = DeployAppletHostManager(self, applet=applet)
        manager.install_applet(**kwargs)

    def save_task(self, task):
        self.task = task
        self.save(update_fields=['task'])
