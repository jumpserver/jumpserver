from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.models import Asset
from assets.models.base import AbsConnectivity
from common.utils import lazyproperty, get_logger
from labels.mixins import LabeledMixin
from .base import BaseAccount
from .mixins import VaultModelMixin
from ..const import SecretType, Source

logger = get_logger(__file__)

__all__ = ['Account', 'AccountHistoricalRecords']


class AccountHistoricalRecords(HistoricalRecords):
    def __init__(self, *args, **kwargs):
        self.updated_version = None
        self.included_fields = kwargs.pop('included_fields', None)
        super().__init__(*args, **kwargs)

    def post_save(self, instance, created, using=None, **kwargs):
        self.updated_version = None
        if getattr(instance, "follows_template", False) and not created:
            return
        if not self.included_fields:
            return super().post_save(instance, created, using=using, **kwargs)
        update_fields = kwargs.get('update_fields')
        credential_fields = set(self.included_fields) - {'id', 'version'}
        if not created and update_fields is not None and not credential_fields.intersection(update_fields):
            return

        # self.updated_version = 0
        if created:
            return super().post_save(instance, created, using=using, **kwargs)

        history_account = instance.history.first()
        if history_account is None:
            return super().post_save(instance, created, using=using, **kwargs)

        check_fields = set(self.included_fields) - {'version'}
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
        local_secret = instance._secret
        try:
            if getattr(instance, 'follows_template', False) and history_type != '-':
                instance._secret = instance.secret
            super().create_historical_record(instance, history_type, using=using)
        finally:
            instance._secret = local_secret
        # Ignore deletion history_type: -
        if self.updated_version is not None and history_type != '-':
            type(instance)._base_manager.db_manager(using=using).filter(
                pk=instance.pk
            ).update(version=self.updated_version)
            self.updated_version = None

    def create_history_model(self, model, inherited):
        if self.included_fields and not self.excluded_fields:
            self.excluded_fields = [
                field.name for field in model._meta.fields
                if field.name not in self.included_fields
            ]
        history_model = super().create_history_model(model, inherited)
        history_model.__module__ = model.__module__
        return history_model


class JSONFilterMixin:
    @staticmethod
    def get_json_filter_attr_q(name, value, match):
        if name == "asset":
            if match == "m2m_all":
                asset_id = (
                    Asset.objects.filter(id__in=value)
                    .annotate(count=models.Count("id"))
                    .filter(count=len(value))
                    .values_list("id", flat=True)
                )
            else:
                asset_id = Asset.objects.filter(id__in=value).values_list("id", flat=True)
            return models.Q(asset_id__in=asset_id)
        return None


class Account(AbsConnectivity, LabeledMixin, BaseAccount, JSONFilterMixin):
    asset = models.ForeignKey(
        'assets.Asset', related_name='accounts',
        on_delete=models.CASCADE, verbose_name=_('Asset')
    )
    su_from = models.ForeignKey(
        'accounts.Account', related_name='su_to', null=True,
        on_delete=models.SET_NULL, verbose_name=_("Su from")
    )
    version = models.IntegerField(default=0, verbose_name=_('Version'))
    history = AccountHistoricalRecords(
        included_fields=['id', '_secret', 'secret_type', 'version'],
        verbose_name=_("historical Account")
    )
    secret_reset = models.BooleanField(default=True, verbose_name=_('Secret reset'))
    source = models.CharField(max_length=30, default=Source.LOCAL, verbose_name=_('Source'))
    source_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Source ID'))
    follow_template = models.BooleanField(default=False, verbose_name=_('Follow template'))
    # Credentials are referenced dynamically; only these properties are copied.
    # Credentials are resolved dynamically; account metadata remains independent.
    TEMPLATE_SYNC_FIELDS = ()

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
            ('view_accountsession', _('Can view session')),
            ('view_accountactivity', _('Can view activity')),
        ]

    TEMPLATE_STATE_FIELDS = ('follow_template', 'source', 'source_id', 'secret_type', 'org_id')

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if set(cls.TEMPLATE_STATE_FIELDS).issubset(field_names):
            instance._loaded_template_state = tuple(
                instance.__dict__[field] for field in cls.TEMPLATE_STATE_FIELDS
            )
        if '_secret' in field_names:
            instance._loaded_secret = instance.__dict__['_secret']
        return instance

    @property
    def follows_template(self):
        return self.source == Source.TEMPLATE and self.follow_template

    def get_source_template(self):
        from .template import AccountTemplate
        from orgs.utils import tmp_to_org

        with tmp_to_org(self.org_id):
            try:
                template = AccountTemplate.objects.filter(
                    id=self.source_id, org_id=self.org_id,
                ).first() if self.source_id else None
            except (DjangoValidationError, ValueError, TypeError):
                template = None
        if template is None:
            raise ValidationError({'source_id': _('The source account template is unavailable.')})
        if template.secret_type != self.secret_type:
            raise ValidationError({'secret_type': _('Account and template secret types must match.')})
        return template

    @property
    def secret(self):
        if self.follows_template:
            template = self.get_source_template()
            secret = template.secret
            if template.secret_has_save_to_vault and not secret:
                from accounts.exceptions import VaultSecretNotFoundException
                raise VaultSecretNotFoundException()
            return secret
        return VaultModelMixin.secret.fget(self)

    @secret.setter
    def secret(self, value):
        if self.follows_template:
            raise ValidationError({'secret': _('Disable template following before editing credentials.')})
        VaultModelMixin.secret.fset(self, value)
        self._secret_explicitly_set = True

    def _set_save_org(self):
        # Match OrgModelMixin before resolving the organization-scoped template.
        from orgs.utils import get_current_org
        org = get_current_org()
        if not org.is_root():
            self.org_id = org.id

    def _get_previous_for_update(self, using):
        if self._state.adding:
            return None
        return type(self)._base_manager.using(using).select_for_update().filter(pk=self.pk).first()

    def _validate_template_transition(self, previous):
        if not previous or not previous.follows_template:
            return
        if self.source != previous.source or self.source_id != previous.source_id:
            raise ValidationError({'source_id': _('Disable template following before changing the source.')})
        if self.follow_template and self.secret_type != previous.secret_type:
            raise ValidationError({'secret_type': _('Disable template following before changing the secret type.')})

    def _prepare_template_detach(self, previous, update_fields):
        """Keep an explicit new credential, otherwise snapshot the template credential."""
        if not previous or not previous.follows_template or self.follow_template:
            return update_fields
        if update_fields is not None and 'follow_template' not in update_fields:
            raise ValidationError({'follow_template': _('Save the following state with the credential snapshot.')})
        if not getattr(self, '_secret_explicitly_set', False):
            if self.secret_type != previous.secret_type:
                raise ValidationError({'secret': _('Provide credentials when changing the secret type.')})
            self.secret = previous.secret
        self._create_vault_on_detach = True
        if update_fields is not None:
            update_fields = list(set(update_fields) | {'_secret'})
        return update_fields

    def _prepare_template_following(self, update_fields):
        """Validate the template reference and discard independent credentials."""
        if not self.follow_template:
            return update_fields
        if not self.follows_template:
            raise ValidationError({'follow_template': _('Only template accounts can follow a template.')})
        self.get_source_template()
        self._secret = None
        if update_fields is not None and 'follow_template' in update_fields:
            update_fields = list(set(update_fields) | {'_secret'})
        return update_fields

    def _save_with_locked_previous(self, previous, *args, **kwargs):
        """Save a transition inside the transaction that locked ``previous``."""
        self._set_save_org()
        self._validate_template_transition(previous)
        update_fields = self._prepare_template_detach(previous, kwargs.get('update_fields'))
        update_fields = self._prepare_template_following(update_fields)
        if update_fields is not None:
            kwargs['update_fields'] = update_fields
        try:
            result = super().save(*args, **kwargs)
            self.__dict__.pop('_secret_explicitly_set', None)
            return result
        finally:
            self.__dict__.pop('_create_vault_on_detach', None)

    def _can_skip_template_transition(self, update_fields):
        if self._state.adding:
            return not self.follow_template
        if getattr(self, '_secret_explicitly_set', False):
            return False
        protected = {*self.TEMPLATE_STATE_FIELDS, 'secret', '_secret'}
        if update_fields is not None and protected.intersection(update_fields):
            return False
        # A full save can also be metadata-only, provided the loaded credential
        # and relationship are unchanged. Deferred values never trigger a read here.
        state = tuple(self.__dict__.get(field) for field in self.TEMPLATE_STATE_FIELDS)
        if getattr(self, '_loaded_template_state', None) != state:
            return False
        if update_fields is None:
            return ('_loaded_secret' in self.__dict__ and '_secret' in self.__dict__
                    and self._loaded_secret == self.__dict__['_secret'])
        return True

    def _prepare_save_kwargs(self, kwargs):
        self._set_save_org()
        if kwargs.get('update_fields') is not None:
            # VaultModelMixin maps the public secret name to the stored field.
            kwargs['update_fields'] = list(kwargs['update_fields'])

    def _save_without_template_transition(self, *args, **kwargs):
        if not self._state.adding and kwargs.get('update_fields') is None:
            # Do not write stale template/credential values during a metadata edit.
            protected = {*self.TEMPLATE_STATE_FIELDS, '_secret', 'version'}
            kwargs['update_fields'] = [
                field.attname for field in self._meta.concrete_fields
                if not field.primary_key and field.attname not in protected
                and field.attname in self.__dict__
            ]
        result = super().save(*args, **kwargs)
        self.__dict__.pop('_secret_explicitly_set', None)
        return result

    def _save_template_transition(self, *args, **kwargs):
        using = kwargs.get('using') or self._state.db or 'default'
        # Keep the credential snapshot and opt-out in the same database transaction.
        with transaction.atomic(using=using):
            previous = self._get_previous_for_update(using)
            return self._save_with_locked_previous(previous, *args, **kwargs)

    def save(self, *args, **kwargs):
        self._prepare_save_kwargs(kwargs)
        if self._can_skip_template_transition(kwargs.get('update_fields')):
            return self._save_without_template_transition(*args, **kwargs)
        return self._save_template_transition(*args, **kwargs)

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
    def alias(self) -> str:
        """
        别称，因为有虚拟账号，@INPUT @MANUAL @USER, 否则为 id
        """
        if self.username.startswith('@'):
            return self.username
        return str(self.id)

    def is_virtual(self) -> bool:
        """
        不要用 username 去判断，因为可能是构造的 account 对象，设置了同名账号的用户名,
        """
        return self.alias.startswith('@')

    def is_ds_account(self) -> bool:
        if self.is_virtual():
            return ''
        if not self.asset.is_directory_service:
            return False
        return True

    @lazyproperty
    def ds(self):
        if not self.is_ds_account():
            return None
        return self.asset.ds

    @lazyproperty
    def ds_domain(self) -> str:
        """这个不能去掉，perm_account 会动态设置这个值，以更改 full_username"""
        if self.is_virtual():
            return ''
        if self.ds and self.ds.domain_name:
            return self.ds.domain_name
        return ''

    def username_has_domain(self):
        return '@' in self.username or '\\' in self.username

    @property
    def full_username(self) -> str:
        if not self.username_has_domain() and self.ds_domain:
            return '{}@{}'.format(self.username, self.ds_domain)
        return self.username

    @lazyproperty
    def has_secret(self) -> bool:
        if self.secret_type == SecretType.SSH_CERTIFICATE:
            return True
        return bool(self.secret)

    @lazyproperty
    def versions(self) -> int:
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
        if su_from.secret_type == SecretType.PASSWORD:
            var['ansible_password'] = self.escape_jinja2_syntax(
                su_from.secret
            )
        elif su_from.secret_type == SecretType.SSH_KEY:
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
        if become_method == 'sudo':
            password = (
                su_from.secret
                if su_from.secret_type == SecretType.PASSWORD
                else None
            )
        else:
            password = (
                self.secret
                if self.secret_type == SecretType.PASSWORD
                else None
            )
        auth['ansible_become'] = True
        auth['ansible_become_method'] = become_method
        auth['ansible_become_user'] = self.username
        if password:
            auth['ansible_become_password'] = (
                self.escape_jinja2_syntax(password)
            )
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

    def update_last_login_date(self):
        Account.objects.filter(pk=self.pk).update(date_last_login=timezone.now())


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
