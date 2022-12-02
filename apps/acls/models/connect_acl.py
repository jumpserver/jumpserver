from django.db import models
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

from common.utils.connection import get_redis_client
from common.const.choices import ConnectMethodChoices
from orgs.mixins.models import OrgManager, OrgModelMixin
from .base import BaseACL, BaseACLQuerySet


class ACLManager(OrgManager):

    def valid(self):
        return self.get_queryset().valid()


class ConnectACL(BaseACL, OrgModelMixin):
    ConnectACLUserCacheKey = 'CONNECT_ACL_USER_{}'
    ConnectACLUserCacheTTL = 600

    class ActionChoices(models.TextChoices):
        reject = 'reject', _('Reject')

    # 用户
    users = models.ManyToManyField(
        'users.User', related_name='connect_acls', blank=True,
        verbose_name=_("User")
    )
    user_groups = models.ManyToManyField(
        'users.UserGroup', related_name='connect_acls', blank=True,
        verbose_name=_("User group"),
    )
    rules = models.JSONField(default=list, verbose_name=_('Rule'))
    # 动作
    action = models.CharField(
        max_length=64, verbose_name=_('Action'),
        choices=ActionChoices.choices, default=ActionChoices.reject
    )

    objects = ACLManager.from_queryset(BaseACLQuerySet)()

    class Meta:
        ordering = ('priority', '-date_updated', 'name')
        verbose_name = _('Connect acl')

    def __str__(self):
        return self.name

    @property
    def rules_display(self):
        return ', '.join(
            [ConnectMethodChoices.get_label(i) for i in self.rules]
        )

    def is_action(self, action):
        return self.action == action

    @staticmethod
    def match(user, connect_type):
        if not user:
            return

        user_acls = user.connect_acls.all().valid().distinct()
        for acl in user_acls:
            if connect_type in acl.rules:
                return acl

        for user_group in user.groups.all():
            acls = user_group.connect_acls.all().valid().distinct()
            for acl in acls:
                if connect_type in acl.rules:
                    return acl

    def _get_all_rules_from_cache(self, user):
        find = False
        cache_key = self.ConnectACLUserCacheKey.format(user.id)
        rules = cache.get(cache_key)
        if rules is not None:
            find = True
        return rules, find

    @staticmethod
    def _get_all_rules_from_db(user):
        connect_rules = set()
        user_acls = user.connect_acls.all().valid()
        user_acl_rules = user_acls.values_list('id', 'rules')
        for r_id, rule in user_acl_rules:
            connect_rules.update(rule)

        for ug in user.groups.all():
            user_group_acls = ug.connect_acls.all().valid()
            user_group_rules = user_group_acls.values_list('id', 'rules')
            for r_id, rule in user_group_rules:
                connect_rules.update(rule)
        return list(connect_rules)

    def set_all_rules_to_cache(self, key, rules):
        cache.set(key, rules, self.ConnectACLUserCacheTTL)

    def all_rules(self, user):
        rules, find = self._get_all_rules_from_cache(user)
        if not find:
            rules = self._get_all_rules_from_db(user)
            self.set_all_rules_to_cache(
                self.ConnectACLUserCacheKey.format(user.id), rules
            )
        return rules

    def clear_rules_cache(self):
        cache.delete_pattern(
            self.ConnectACLUserCacheKey.format('*')
        )

    def save(self, *args, **kwargs):
        self.clear_rules_cache()
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        self.clear_rules_cache()
        return super().delete(using=using, keep_parents=keep_parents)
