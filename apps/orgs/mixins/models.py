# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from common.utils import get_logger
from ..utils import (
    set_current_org, get_current_org, current_org,
    filter_org_queryset
)
from ..models import Organization

logger = get_logger(__file__)

__all__ = [
    'OrgManager', 'OrgModelMixin',
]


class OrgManager(models.Manager):

    def get_queryset(self):
        queryset = super(OrgManager, self).get_queryset()
        return filter_org_queryset(queryset)

    def all(self):
        if not current_org:
            msg = 'You can `objects.set_current_org(org).all()` then run it'
            return self
        else:
            return super(OrgManager, self).all()

    def set_current_org(self, org):
        if isinstance(org, str):
            org = Organization.get_instance(org)
        set_current_org(org)
        return self


class OrgModelMixin(models.Model):
    org_id = models.CharField(max_length=36, blank=True, default='',
                              verbose_name=_("Organization"), db_index=True)
    objects = OrgManager()

    sep = '@'

    def save(self, *args, **kwargs):
        org = get_current_org()
        if org is None:
            return super().save(*args, **kwargs)

        if org.is_real() or org.is_system():
            self.org_id = org.id
        elif org.is_default():
            self.org_id = ''
        return super().save(*args, **kwargs)

    @property
    def org(self):
        from orgs.models import Organization
        org = Organization.get_instance(self.org_id)
        return org

    @property
    def org_name(self):
        return self.org.name

    @property
    def fullname(self, attr=None):
        name = ''
        if attr and hasattr(self, attr):
            name = getattr(self, attr)
        elif hasattr(self, 'name'):
            name = self.name
        elif hasattr(self, 'hostname'):
            name = self.hostname
        if self.org.is_real():
            return name + self.sep + self.org_name
        else:
            return name

    def validate_unique(self, exclude=None):
        """
        Check unique constraints on the model and raise ValidationError if any
        failed.
        Form 提交时会使用这个检验
        """
        self.org_id = current_org.id if current_org.is_real() else ''
        if exclude and 'org_id' in exclude:
            exclude.remove('org_id')
        unique_checks, date_checks = self._get_unique_checks(exclude=exclude)

        errors = self._perform_unique_checks(unique_checks)
        date_errors = self._perform_date_checks(date_checks)

        for k, v in date_errors.items():
            errors.setdefault(k, []).extend(v)

        if errors:
            raise ValidationError(errors)

    class Meta:
        abstract = True
