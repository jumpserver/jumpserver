# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from orgs.mixins.models import JMSOrgBaseModel

__all__ = ['UserGroup']


class UserGroup(JMSOrgBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'))

    def __str__(self):
        return self.name

    @lazyproperty
    def users_amount(self):
        return self.users.count()

    class Meta:
        ordering = ['name']
        unique_together = [('org_id', 'name'), ]
        verbose_name = _("User group")

    @classmethod
    def initial(cls):
        default_group = cls.objects.filter(name='Default')
        if not default_group:
            group = cls(name='Default', created_by='System', comment='Default user group')
            group.save()
        else:
            group = default_group[0]
        return group
