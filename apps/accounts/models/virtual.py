from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.const import AliasAccount
from orgs.mixins.models import JMSOrgBaseModel

__all__ = ['VirtualAccount']

from orgs.utils import tmp_to_org


class VirtualAccount(JMSOrgBaseModel):
    alias = models.CharField(max_length=128, choices=AliasAccount.virtual_choices(), verbose_name=_('Alias'), )
    secret_from_login = models.BooleanField(default=None, null=True, verbose_name=_("Secret from login"), )

    class Meta:
        unique_together = [('alias', 'org_id')]

    @property
    def name(self):
        return self.get_alias_display()

    @property
    def username(self):
        usernames_map = {
            AliasAccount.INPUT: _("Manual input"),
            AliasAccount.USER: _("Same with user"),
            AliasAccount.ANON: ''
        }
        usernames_map = {str(k): v for k, v in usernames_map.items()}
        return usernames_map.get(self.alias, '')

    @property
    def comment(self):
        comments_map = {
            AliasAccount.INPUT: _('Non-asset account, Input username/password on connect'),
            AliasAccount.USER: _('The account username name same with user on connect'),
            AliasAccount.ANON: _('Connect asset without using a username and password, '
                                 'and it only supports web-based and custom-type assets'),
        }
        comments_map = {str(k): v for k, v in comments_map.items()}
        return comments_map.get(self.alias, '')

    @classmethod
    def get_or_init_queryset(cls):
        aliases = [i[0] for i in AliasAccount.virtual_choices()]
        alias_created = cls.objects.all().values_list('alias', flat=True)
        need_created = set(aliases) - set(alias_created)

        if need_created:
            accounts = [cls(alias=alias) for alias in need_created]
            cls.objects.bulk_create(accounts, ignore_conflicts=True)
        return cls.objects.all()

    @classmethod
    def get_special_account(cls, alias, user, asset, input_username='', input_secret='', from_permed=True):
        if alias == AliasAccount.INPUT.value:
            account = cls.get_manual_account(input_username, input_secret, from_permed)
        elif alias == AliasAccount.ANON.value:
            account = cls.get_anonymous_account()
        elif alias == AliasAccount.USER.value:
            account = cls.get_same_account(user, asset, input_secret=input_secret, from_permed=from_permed)
        else:
            account = cls(name=alias, username=alias, secret=None)
        account.alias = alias
        if asset:
            account.asset = asset
            account.org_id = asset.org_id
        return account

    @classmethod
    def get_manual_account(cls, input_username='', input_secret='', from_permed=True):
        """ @INPUT 手动登录的账号(any) """
        from .account import Account
        if from_permed:
            username = AliasAccount.INPUT.value
            secret = ''
        else:
            username = input_username
            secret = input_secret
        return Account(name=AliasAccount.INPUT.label, username=username, secret=secret)

    @classmethod
    def get_anonymous_account(cls):
        from .account import Account
        return Account(name=AliasAccount.ANON.label, username=AliasAccount.ANON.value, secret=None)

    @classmethod
    def get_same_account(cls, user, asset, input_secret='', from_permed=True):
        """ @USER 动态用户的账号(self) """
        from .account import Account
        username = user.username

        with tmp_to_org(asset.org):
            same_account = cls.objects.filter(alias='@USER').first()

        secret = ''
        if same_account and same_account.secret_from_login:
            secret = user.get_cached_password_if_has()

        if not secret and not from_permed:
            secret = input_secret
        return Account(name=AliasAccount.USER.label, username=username, secret=secret)
