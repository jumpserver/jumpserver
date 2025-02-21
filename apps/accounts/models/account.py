from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.models.base import AbsConnectivity
from common.utils import lazyproperty, get_logger
from labels.mixins import LabeledMixin
from .base import BaseAccount
from .mixins import VaultModelMixin
from ..const import Source

logger = get_logger(__file__)

__all__ = ['Account', 'AccountHistoricalRecords']


class AccountHistoricalRecords(HistoricalRecords):
    def __init__(self, *args, **kwargs):
        self.updated_version = None
        self.included_fields = kwargs.pop('included_fields', None)
        super().__init__(*args, **kwargs)

    def post_save(self, instance, created, using=None, **kwargs):
        if not self.included_fields:
            return super().post_save(instance, created, using=using, **kwargs)

        check_fields = set(self.included_fields) - {'version'}

        history_account = instance.history.first()
        if history_account is None:
            self.updated_version = 0
            return super().post_save(instance, created, using=using, **kwargs)

        history_attrs = {field: getattr(history_account, field) for field in check_fields}

        attrs = {field: getattr(instance, field) for field in check_fields}
        history_attrs = set(history_attrs.items())
        attrs = set(attrs.items())
        diff = attrs - history_attrs
        if not diff:
            return
        self.updated_version = history_account.version + 1
        instance.version = self.updated_version
        return super().post_save(instance, created, using=using, **kwargs)

    def create_historical_record(self, instance, history_type, using=None):
        super().create_historical_record(instance, history_type, using=using)
        # Ignore deletion history_type: -
        if self.updated_version is not None and history_type != '-':
            instance.save(update_fields=['version'])

    def create_history_model(self, model, inherited):
        if self.included_fields and not self.excluded_fields:
            self.excluded_fields = [
                field.name for field in model._meta.fields
                if field.name not in self.included_fields
            ]
        return super().create_history_model(model, inherited)


class Account(AbsConnectivity, LabeledMixin, BaseAccount):
    asset = models.ForeignKey(
        'assets.Asset', related_name='accounts',
        on_delete=models.CASCADE, verbose_name=_('Asset')
    )
    su_from = models.ForeignKey(
        'accounts.Account', related_name='su_to', null=True,
        on_delete=models.SET_NULL, verbose_name=_("Su from")
    )
    version = models.IntegerField(default=0, verbose_name=_('Version'))
    history = AccountHistoricalRecords(included_fields=['id', '_secret', 'secret_type', 'version'],
                                       verbose_name=_("historical Account"))
    secret_reset = models.BooleanField(default=True, verbose_name=_('Secret reset'))
    source = models.CharField(max_length=30, default=Source.LOCAL, verbose_name=_('Source'))
    source_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Source ID'))
    date_last_login = models.DateTimeField(null=True, blank=True, verbose_name=_('Date last access'))
    login_by = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Access by'))
    date_change_secret = models.DateTimeField(null=True, blank=True, verbose_name=_('Date change secret'))
    change_secret_status = models.CharField(
        max_length=16, null=True, blank=True, verbose_name=_('Change secret status')
    )

    class Meta:
        verbose_name = _('Account')
        unique_together = [
            ('username', 'asset', 'secret_type'),
            ('name', 'asset'),
        ]
        permissions = [
            ('view_accountsecret', _('Can view asset account secret')),
            ('view_historyaccount', _('Can view asset history account')),
            ('view_historyaccountsecret', _('Can view asset history account secret')),
            ('verify_account', _('Can verify account')),
            ('push_account', _('Can push account')),
            ('remove_account', _('Can remove account')),
        ]

    def __str__(self):
        if self.asset_id:
            host = self.asset.name
        else:
            host = 'Dynamic'
        return '{}({})'.format(self.name, host)

    @lazyproperty
    def platform(self):
        return self.asset.platform

    @lazyproperty
    def alias(self):
        if self.username.startswith('@'):
            return self.username
        return self.name

    @lazyproperty
    def has_secret(self):
        return bool(self.secret)

    @lazyproperty
    def versions(self):
        return self.history.count()

    def get_su_from_accounts(self):
        """ 排除自己和以自己为 su-from 的账号 """
        return self.asset.accounts.exclude(id=self.id).exclude(su_from=self)

    def make_account_ansible_vars(self, su_from):
        var = {
            'ansible_user': su_from.username,
        }
        if not su_from.secret:
            return var
        var['ansible_password'] = self.escape_jinja2_syntax(su_from.secret)
        var['ansible_ssh_private_key_file'] = su_from.private_key_path
        return var

    def get_ansible_become_auth(self):
        su_from = self.su_from
        platform = self.platform
        auth = {'ansible_become': False}
        if not (platform.su_enabled and su_from):
            return auth

        auth.update(self.make_account_ansible_vars(su_from))

        become_method = platform.ansible_become_method
        password = su_from.secret if become_method == 'sudo' else self.secret
        auth['ansible_become'] = True
        auth['ansible_become_method'] = become_method
        auth['ansible_become_user'] = self.username
        auth['ansible_become_password'] = self.escape_jinja2_syntax(password)
        return auth

    @staticmethod
    def escape_jinja2_syntax(value):
        if not isinstance(value, str):
            return value

        def escape(v):
            v = v.replace('{{', '__TEMP_OPEN_BRACES__') \
                .replace('}}', '__TEMP_CLOSE_BRACES__')

            v = v.replace('__TEMP_OPEN_BRACES__', '{{ "{{" }}') \
                .replace('__TEMP_CLOSE_BRACES__', '{{ "}}" }}')

            return v.replace('{%', '{{ "{%" }}').replace('%}', '{{ "%}" }}')

        return escape(value)


def replace_history_model_with_mixin():
    """
    替换历史模型中的父类为指定的Mixin类。

    Parameters:
        model (class): 历史模型类，例如 Account.history.model
        mixin_class (class): 要替换为的Mixin类

    Returns:
        None
    """
    model = Account.history.model
    model.__bases__ = (VaultModelMixin,) + model.__bases__


replace_history_model_with_mixin()
