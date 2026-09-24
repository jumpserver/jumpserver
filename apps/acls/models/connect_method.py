from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.fields import JSONManyToManyField
from .base import UserBaseACL

__all__ = ['ConnectMethodACL']


class ConnectMethodACL(UserBaseACL):
    # Empty and "all" preserve the existing user-wide rules. Explicit asset
    # selections take precedence over those rules for the selected methods.
    assets = JSONManyToManyField(
        'assets.Asset', default=dict, blank=True, verbose_name=_('Assets')
    )
    connect_methods = models.JSONField(default=list, verbose_name=_('Connect methods'))

    class Meta(UserBaseACL.Meta):
        verbose_name = _('Connect method acl')
        abstract = False

    @classmethod
    def get_user_disabled_methods(cls, user, asset=None):
        queryset = cls.get_user_acls(user).filter(
            action__in=[cls.ActionChoices.accept, cls.ActionChoices.reject]
        )
        global_filter = models.Q(assets={}) | models.Q(assets__type='all')
        if asset is None:
            queryset = queryset.filter(global_filter)
        else:
            queryset = queryset.filter(global_filter | cls.assets.get_filter_q(asset))

        accepted = set()
        rejected = set()
        # A scoped rule wins over a global rule. Within scoped rules the lowest
        # priority number wins, and a reject wins a tie.
        scoped = {}
        for acl in queryset.order_by('priority', 'name'):
            methods = acl.connect_methods or []
            scope = acl.assets.value.get('type') if isinstance(acl.assets.value, dict) else None
            if scope in ('ids', 'attrs'):
                for method in methods:
                    decision = scoped.get(method)
                    candidate = (acl.priority, acl.action != cls.ActionChoices.reject)
                    if decision is None or candidate < decision[0]:
                        scoped[method] = (candidate, acl.action)
            elif acl.action == cls.ActionChoices.accept:
                accepted.update(methods)
            else:
                rejected.update(methods)

        disabled = rejected - accepted
        for method, (_, action) in scoped.items():
            if action == cls.ActionChoices.reject:
                disabled.add(method)
            else:
                disabled.discard(method)
        return disabled

    @classmethod
    def is_method_allowed(cls, user, asset, method, protocol=None):
        # Koko's direct SSH/SFTP sessions send the protocol as the method.
        # They are the same native entry points shown in the method picker.
        if method == 'sftp' or (method == 'ssh' and protocol == 'sftp'):
            method = 'sftp_client'
        elif method == 'ssh':
            method = 'ssh_client'
        return method not in cls.get_user_disabled_methods(user, asset)
