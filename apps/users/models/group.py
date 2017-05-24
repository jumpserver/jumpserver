#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.db import models, IntegrityError
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _

from common.utils import signer, date_expired_default
from common.mixins import NoDeleteModelMixin

__all__ = ['UserGroup']


class UserGroup(NoDeleteModelMixin):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True, null=True,
                                        verbose_name=_('Date created'))
    created_by = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name
    __str__ = __unicode__

    def delete(self, using=None, keep_parents=False):
        if self.name != 'Default':
            self.users.clear()
            return super(UserGroup, self).delete()
        return True

    class Meta:
        ordering = ['name']

    @classmethod
    def initial(cls):
        default_group = cls.objects.filter(name='Default')
        if not default_group:
            group = cls(name='Default', created_by='System', comment='Default user group')
            group.save()
        else:
            group = default_group[0]
        return group

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed, choice
        import forgery_py
        from . import User

        seed()
        for i in range(count):
            group = cls(name=forgery_py.name.full_name(),
                        comment=forgery_py.lorem_ipsum.sentence(),
                        created_by=choice(User.objects.all()).username)
            try:
                group.save()
            except IntegrityError:
                print('Error continue')
                continue
