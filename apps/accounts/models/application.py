from django.db import models
from django.utils.translation import gettext_lazy as _
from private_storage.fields import PrivateImageField

from accounts.models import Account
from common.db import fields
from common.db.fields import JSONManyToManyField, RelatedManager
from common.db.utils import default_ip_group
from common.utils import random_string
from orgs.mixins.models import JMSOrgBaseModel


class IntegrationApplication(JMSOrgBaseModel):
    is_anonymous = False

    name = models.CharField(max_length=128, unique=False, verbose_name=_('Name'))
    logo = PrivateImageField(
        upload_to='images', max_length=128, verbose_name=_('Logo')
    )
    secret = fields.EncryptTextField(default='', verbose_name=_('Secret'))
    accounts = JSONManyToManyField('accounts.Account', default=dict, verbose_name=_('Accounts'))
    ip_group = models.JSONField(default=default_ip_group, verbose_name=_('IP group'))
    date_last_used = models.DateTimeField(null=True, blank=True, verbose_name=_('Date last used'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))

    class Meta:
        unique_together = [('name', 'org_id')]
        verbose_name = _('Integration App')

    def get_accounts(self):
        qs = Account.objects.all()
        query = RelatedManager.get_to_filter_qs(self.accounts.value, Account)
        return qs.filter(*query)

    @property
    def accounts_amount(self):
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

    def get_secret(self):
        self.secret = random_string(36)
        self.save(update_fields=['secret'])
        return self.secret

    def get_account(self, asset='', asset_id='', account='', account_id=''):
        qs = Account.objects.all()
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
