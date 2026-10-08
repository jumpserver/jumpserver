from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from private_storage.fields import PrivateImageField
from rest_framework.exceptions import PermissionDenied

from accounts.const import ApplicationEvent, WebhookRequestMethod
from accounts.models import Account
from common.db import fields
from common.db.fields import JSONManyToManyField, RelatedManager
from common.db.utils import default_ip_group
from common.utils import random_string
from orgs.mixins.models import JMSOrgBaseModel


def empty_application_accounts():
    return {'type': 'ids', 'ids': []}


class IntegrationApplication(JMSOrgBaseModel):
    is_anonymous = False

    name = models.CharField(max_length=128, unique=False, verbose_name=_('Name'))
    logo = PrivateImageField(
        upload_to='images', max_length=128, verbose_name=_('Logo')
    )
    secret = fields.EncryptTextField(default='', verbose_name=_('Secret'))
    accounts = JSONManyToManyField(
        'accounts.Account', default=empty_application_accounts,
        allow_empty_ids=True, verbose_name=_('Accounts'),
    )
    enforce_account_limit = models.BooleanField(default=True, editable=False)
    ip_group = models.JSONField(default=default_ip_group, verbose_name=_('IP group'))
    date_last_used = models.DateTimeField(null=True, blank=True, verbose_name=_('Date last used'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))

    class Meta:
        unique_together = [('name', 'org_id')]
        verbose_name = _('Integration App')

    def get_accounts(self):
        qs = Account.objects.filter(org_id=self.org_id)
        query = RelatedManager.get_to_filter_qs(self.accounts.value, Account)
        return qs.filter(*query)

    def assert_account_limit(self):
        if not self.enforce_account_limit:
            return
        limit = settings.APPLICATION_ACCOUNT_SCOPE_LIMIT
        if self.get_accounts().distinct().values_list('id', flat=True)[:limit + 1].count() > limit:
            raise PermissionDenied(
                _('The application account scope exceeds the configured limit.'),
                code='application_account_limit_exceeded',
            )

    @property
    def accounts_amount(self) -> int:
        return self.get_accounts().count()

    @property
    def is_valid(self):
        return self.is_active

    @property
    def is_authenticated(self):
        return self.is_active

    @staticmethod
    def has_perms(perms):
        support_perms = ['accounts.view_integrationapplication']
        return all([perm in support_perms for perm in perms])

    def refresh_secret(self):
        self.secret = random_string(36)
        self.save(update_fields=['secret'])
        return self.secret

    def get_account(self, asset='', asset_id='', account='', account_id=''):
        self.assert_account_limit()
        qs = Account.objects.filter(org_id=self.org_id)
        if account_id:
            qs = qs.filter(id=account_id)
        elif account:
            qs = qs.filter(name=account)
            if asset_id:
                qs = qs.filter(asset_id=asset_id)
            elif asset:
                qs = qs.filter(asset__name=asset)
        query = RelatedManager.get_to_filter_qs(self.accounts.value, Account)
        return qs.filter(*query).distinct().first()


def default_application_webhook_events():
    return list(ApplicationEvent.values)


def default_application_webhook_template():
    return {
        'event_id': '{{ event.id }}',
        'event': '{{ event.code }}',
        'result': '{{ event.result }}',
        'application': '{{ application.name }}',
        'credential_key': '{{ credential.key }}',
        'credential_revision': '{{ credential.revision }}',
        'summary': '{{ event.summary }}',
        'occurred_at': '{{ event.occurred_at }}',
    }


class ApplicationWebhook(JMSOrgBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    applications = models.ManyToManyField(
        IntegrationApplication, related_name='webhook_rules',
        verbose_name=_('Integration applications'),
    )
    is_active = models.BooleanField(default=False, verbose_name=_('Active'))
    url = fields.EncryptTextField(default='', blank=True, max_length=2048, verbose_name=_('URL'))
    method = models.CharField(
        max_length=8, choices=WebhookRequestMethod.choices,
        default=WebhookRequestMethod.POST, verbose_name=_('Request method'),
    )
    headers = fields.EncryptJsonDictTextField(default=dict, blank=True, verbose_name=_('Request headers'))
    events = models.JSONField(default=default_application_webhook_events, verbose_name=_('Events'))
    body_template = models.JSONField(
        default=default_application_webhook_template, verbose_name=_('Body template'),
    )

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('Application webhook')
