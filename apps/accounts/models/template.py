from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from labels.mixins import LabeledMixin
from .account import Account
from .base import BaseAccount, SecretWithRandomMixin

__all__ = ['AccountTemplate', ]


class AccountTemplate(LabeledMixin, BaseAccount, SecretWithRandomMixin):
    su_from = models.ForeignKey(
        'self', related_name='su_to', null=True,
        on_delete=models.SET_NULL, verbose_name=_("Su from")
    )
    auto_push = models.BooleanField(default=False, verbose_name=_('Auto push'))
    platforms = models.ManyToManyField(
        'assets.Platform', related_name='account_templates',
        verbose_name=_('Platforms'), blank=True,
    )
    push_params = models.JSONField(default=dict, verbose_name=_('Push params'))

    class Meta:
        verbose_name = _('Account template')
        unique_together = (
            ('name', 'org_id'),
        )
        permissions = [
            ('view_accounttemplatesecret', _('Can view asset account template secret')),
            ('change_accounttemplatesecret', _('Can change asset account template secret')),
        ]

    def __str__(self):
        return f'{self.name}({self.username})'

    @classmethod
    def get_su_from_account_templates(cls, pk=None):
        if pk is None:
            return cls.objects.all()
        return cls.objects.exclude(Q(id=pk) | Q(su_from_id=pk))

    def get_su_from_account(self, asset):
        su_from = self.su_from
        if su_from and asset.platform.su_enabled:
            account = asset.accounts.filter(
                username=su_from.username,
                secret_type=su_from.secret_type
            ).first()
            return account

    def bulk_update_accounts(self, accounts):
        history_model = Account.history.model
        account_ids = accounts.values_list('id', flat=True)
        history_accounts = history_model.objects.filter(id__in=account_ids)
        account_id_count_map = {
            str(i['id']): i['count']
            for i in history_accounts.values('id').order_by('id')
            .annotate(count=Count(1)).values('id', 'count')
        }

        for account in accounts:
            account_id = str(account.id)
            account.version = account_id_count_map.get(account_id) + 1
            account.secret = self.get_secret()
        Account.objects.bulk_update(accounts, ['version', 'secret'])

    @staticmethod
    def bulk_create_history_accounts(accounts, user_id):
        history_model = Account.history.model
        history_account_objs = []
        for account in accounts:
            history_account_objs.append(
                history_model(
                    id=account.id,
                    version=account.version,
                    secret=account.secret,
                    secret_type=account.secret_type,
                    history_user_id=user_id,
                    history_date=timezone.now()
                )
            )
        history_model.objects.bulk_create(history_account_objs)

    def bulk_sync_account_secret(self, accounts, user_id):
        """ 批量同步账号密码 """
        self.bulk_update_accounts(accounts)
        self.bulk_create_history_accounts(accounts, user_id)
