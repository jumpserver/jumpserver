import base64
import json
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied

from accounts.models import VirtualAccount
from assets.const import Protocol
from assets.const.host import GATEWAY_NAME
from common.db.fields import EncryptTextField
from common.exceptions import JMSException
from common.utils import lazyproperty, pretty_string, bulk_get
from common.utils.timezone import as_current_tz
from orgs.mixins.models import JMSOrgBaseModel
from orgs.utils import tmp_to_org
from terminal.models import Applet, VirtualApp


def date_expired_default():
    return timezone.now() + timedelta(seconds=settings.CONNECTION_TOKEN_ONETIME_EXPIRATION)


class ConnectionToken(JMSOrgBaseModel):
    value = models.CharField(max_length=64, default='', verbose_name=_("Value"))
    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='connection_tokens', verbose_name=_('User')
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='connection_tokens', verbose_name=_('Asset'),
    )
    account = models.CharField(max_length=128, verbose_name=_("Account name"))  # 登录账号Name
    input_username = models.CharField(max_length=128, default='', blank=True, verbose_name=_("Input username"))
    input_secret = EncryptTextField(max_length=64, default='', blank=True, verbose_name=_("Input secret"))
    protocol = models.CharField(max_length=16, default=Protocol.ssh, verbose_name=_("Protocol"))
    connect_method = models.CharField(max_length=32, verbose_name=_("Connect method"))
    connect_options = models.JSONField(default=dict, verbose_name=_("Connect options"))
    user_display = models.CharField(max_length=128, default='', verbose_name=_("User display"))
    asset_display = models.CharField(max_length=128, default='', verbose_name=_("Asset display"))
    is_reusable = models.BooleanField(default=False, verbose_name=_("Reusable"))
    date_expired = models.DateTimeField(default=date_expired_default, verbose_name=_("Date expired"))
    from_ticket = models.OneToOneField(
        'tickets.ApplyLoginAssetTicket', related_name='connection_token',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('From ticket')
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        ordering = ('-date_expired',)
        permissions = [
            ('expire_connectiontoken', _('Can expire connection token')),
            ('reuse_connectiontoken', _('Can reuse connection token')),
        ]
        verbose_name = _('Connection token')

    @property
    def is_expired(self):
        return self.date_expired < timezone.now()

    @property
    def expire_time(self):
        interval = self.date_expired - timezone.now()
        seconds = interval.total_seconds()
        if seconds < 0:
            seconds = 0
        return int(seconds)

    def save(self, *args, **kwargs):
        self.asset_display = pretty_string(self.asset, max_length=128)
        self.user_display = pretty_string(self.user, max_length=128)
        return super().save(*args, **kwargs)

    def expire(self):
        self.date_expired = timezone.now()
        self.save(update_fields=['date_expired'])

    def set_reusable(self, is_reusable):
        self.is_reusable = is_reusable
        if self.is_reusable:
            seconds = settings.CONNECTION_TOKEN_REUSABLE_EXPIRATION
        else:
            seconds = settings.CONNECTION_TOKEN_ONETIME_EXPIRATION
        self.date_expired = timezone.now() + timedelta(seconds=seconds)
        self.save(update_fields=['is_reusable', 'date_expired'])

    def renewal(self):
        """ 续期 Token，将来支持用户自定义创建 token 后，续期策略要修改 """
        self.date_expired = date_expired_default()
        self.save()

    @lazyproperty
    def permed_account(self):
        from perms.utils import PermAssetDetailUtil
        permed_account = PermAssetDetailUtil(self.user, self.asset) \
            .validate_permission(self.account, self.protocol)
        return permed_account

    @lazyproperty
    def actions(self):
        return self.permed_account.actions

    @lazyproperty
    def expire_at(self):
        return self.permed_account.date_expired.timestamp()

    def is_valid(self):
        if not self.is_active:
            error = _('Connection token inactive')
            raise PermissionDenied(error)

        if self.is_expired:
            error = _('Connection token expired at: {}').format(as_current_tz(self.date_expired))
            raise PermissionDenied(error)
        if not self.user or not self.user.is_valid:
            error = _('No user or invalid user')
            raise PermissionDenied(error)
        if not self.asset or not self.asset.is_active:
            error = _('No asset or inactive asset')
            raise PermissionDenied(error)
        if not self.account:
            error = _('No account')
            raise PermissionDenied(error)

        if timezone.now() - self.date_created < timedelta(seconds=60):
            return True, None

        if not self.permed_account or not self.permed_account.actions:
            msg = 'user `{}` not has asset `{}` permission for login `{}`'.format(
                self.user, self.asset, self.account
            )
            raise PermissionDenied(msg)

        if self.permed_account.date_expired < timezone.now():
            raise PermissionDenied('Expired')
        return True

    @lazyproperty
    def platform(self):
        return self.asset.platform

    @lazyproperty
    def connect_method_object(self):
        from common.utils import get_request_os
        from jumpserver.utils import get_current_request
        from terminal.connect_methods import ConnectMethodUtil

        request = get_current_request()
        os = get_request_os(request) if request else 'windows'
        method = ConnectMethodUtil.get_connect_method(
            self.connect_method, protocol=self.protocol, os=os
        )
        return method

    def get_remote_app_option(self):
        cmdline = {
            'app_name': self.connect_method,
            'user_id': str(self.user.id),
            'asset_id': str(self.asset.id),
            'token_id': str(self.id)
        }
        cmdline_b64 = base64.b64encode(json.dumps(cmdline).encode()).decode()
        app = '||tinker'
        options = {
            'remoteapplicationmode:i': '1',
            'remoteapplicationprogram:s': app,
            'remoteapplicationname:s': app,
            'alternate shell:s': app,
            'remoteapplicationcmdline:s': cmdline_b64,
            'disableconnectionsharing:i': '1',
        }
        return options

    def get_virtual_app_option(self):
        method = self.connect_method_object
        if not method or method.get('type') != 'virtual_app' or method.get('disabled', False):
            return None
        virtual_app = VirtualApp.objects.filter(name=method.get('value')).first()
        if not virtual_app:
            return None
        return virtual_app

    def get_applet_option(self):
        method = self.connect_method_object
        if not method or method.get('type') != 'applet' or method.get('disabled', False):
            return None

        applet = Applet.objects.filter(name=method.get('value')).first()
        if not applet:
            return None

        host_account = applet.select_host_account(self.user, self.asset)
        if not host_account:
            raise JMSException({'error': 'No host account available'})

        host, account, lock_key = bulk_get(host_account, ('host', 'account', 'lock_key'))
        gateway = host.domain.select_gateway() if host.domain else None

        data = {
            'id': lock_key,
            'applet': applet,
            'host': host,
            'gateway': gateway,
            'account': account,
            'remote_app_option': self.get_remote_app_option()
        }
        return data

    @staticmethod
    def release_applet_account(lock_key):
        if lock_key:
            cache.delete(lock_key)
            return True

    @lazyproperty
    def account_object(self):
        if not self.asset:
            return None

        if self.account.startswith('@'):
            account = VirtualAccount.get_special_account(
                self.account, self.user, self.asset, input_username=self.input_username,
                input_secret=self.input_secret, from_permed=False
            )
        else:
            account = self.asset.accounts.filter(name=self.account).first()
            if not account.secret and self.input_secret:
                account.secret = self.input_secret
        return account

    @lazyproperty
    def domain(self):
        if not self.asset.platform.domain_enabled:
            return
        if self.asset.platform.name == GATEWAY_NAME:
            return
        domain = self.asset.domain if self.asset.domain else None
        return domain

    @lazyproperty
    def gateway(self):
        if not self.asset or not self.domain:
            return
        return self.asset.gateway

    @lazyproperty
    def command_filter_acls(self):
        from acls.models import CommandFilterACL
        kwargs = {
            'user': self.user,
            'asset': self.asset,
            'account': self.account_object,
        }
        with tmp_to_org(self.asset.org_id):
            acls = CommandFilterACL.filter_queryset(**kwargs).valid()
        return acls


class SuperConnectionToken(ConnectionToken):
    class Meta:
        proxy = True
        permissions = [
            ('view_superconnectiontokensecret', _('Can view super connection token secret'))
        ]
        verbose_name = _("Super connection token")
