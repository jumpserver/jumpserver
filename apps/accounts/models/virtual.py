from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.const import AliasAccount
from orgs.mixins.models import JMSOrgBaseModel

__all__ = ['VirtualAccount']


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
        comments = {
            AliasAccount.INPUT: _('Non-asset account, Input username/password on connect'),
            AliasAccount.USER: _('The account username name same with user on connect'),
            AliasAccount.ANON: _('Connect asset without using a username and password, '
                                 'and it only supports web-based and custom-type assets'),
        }
        comments = {str(k): v for k, v in comments.items()}
        return comments.get(self.alias, '')

    @classmethod
    def get_or_create_queryset(cls):
        aliases = [i[0] for i in AliasAccount.virtual_choices()]
        alias_created = cls.objects.all().values_list('alias', flat=True)
        need_created = set(aliases) - set(alias_created)

        if need_created:
            accounts = [cls(alias=alias) for alias in need_created]
            cls.objects.bulk_create(accounts, ignore_conflicts=True)
        return cls.objects.all()
