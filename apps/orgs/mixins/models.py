# -*- coding: utf-8 -*-
#
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from common.db.models import JMSBaseModel
from common.db.utils import Encryptor
from common.utils import get_logger, lazyproperty
from ..models import Organization
from ..utils import (
    set_current_org, get_current_org, current_org, filter_org_queryset
)

logger = get_logger(__file__)

__all__ = [
    'OrgManager', 'OrgModelMixin', 'JMSOrgBaseModel', 'VaultModelMixin'
]


class OrgManager(models.Manager):
    def all_group_by_org(self):
        from ..models import Organization
        orgs = list(Organization.objects.all())
        org_queryset = {}
        for org in orgs:
            org_id = org.id
            queryset = super(OrgManager, self).get_queryset().filter(org_id=org_id)
            org_queryset[org] = queryset
        return org_queryset

    def get_queryset(self):
        queryset = super(OrgManager, self).get_queryset()
        return filter_org_queryset(queryset)

    def set_current_org(self, org):
        if isinstance(org, str):
            org = Organization.get_instance(org)
        set_current_org(org)
        return self

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        org = get_current_org()
        for obj in objs:
            if org.is_root():
                if not obj.org_id:
                    raise ValidationError('Please save in a org')
            else:
                obj.org_id = org.id
        return super().bulk_create(objs, batch_size, ignore_conflicts)


class OrgModelMixin(models.Model):
    org_id = models.CharField(
        max_length=36, blank=True, default='',
        verbose_name=_("Organization"), db_index=True
    )
    objects = OrgManager()
    sep = '@'

    def save(self, *args, **kwargs):
        locking_org = getattr(self, 'LOCKING_ORG', None)
        if locking_org:
            org = Organization.get_instance(locking_org)
        else:
            org = get_current_org()
        # 这里不可以优化成, 因为 root 组织下可以设置组织 id 来保存
        # if org.is_root() and not self.org_id:
        #     raise ...
        if org.is_root():
            if not self.org_id:
                raise ValidationError('Please save in a org')
        else:
            self.org_id = org.id
        return super().save(*args, **kwargs)

    @lazyproperty
    def org(self):
        return Organization.get_instance(self.org_id)

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
        return name + self.sep + self.org_name

    def validate_unique(self, exclude=None):
        """
        Check unique constraints on the model and raise ValidationError if any
        failed.
        Form 提交时会使用这个检验
        """
        self.org_id = current_org.id
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


class JMSOrgBaseModel(JMSBaseModel, OrgModelMixin):
    class Meta:
        abstract = True


class VaultModelMixin(models.Model):
    _secret = models.TextField(blank=True, null=True, verbose_name=_('Secret'))
    cache_secret: Any
    is_sync_secret = False

    class Meta:
        abstract = True

    @property
    def secret(self):
        from accounts.backends import get_vault_client
        value = get_vault_client(self).get().get('secret')
        value = Encryptor(value).decrypt()

        # 查一遍 local 数据库
        local_secret = Encryptor(self._secret).decrypt()
        value = value or local_secret
        return value

    @secret.setter
    def secret(self, value):
        if value is not None:
            value = Encryptor(value).encrypt()

        self.is_sync_secret = True
        self._secret = value

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # 通过 post_save signal 处理 secret 数据


class VaultQuerySetMixin(models.QuerySet):

    def update(self, **kwargs):
        from accounts.const import VaultType
        exist_secret = 'secret' in kwargs
        is_local = settings.VAULT_TYPE == VaultType.LOCAL

        secret = kwargs.pop('secret', None)
        if exist_secret:
            kwargs['_secret'] = secret

        super().update(**kwargs)

        if is_local:
            return

        ids = self.values_list('id', flat=True)
        qs = self.model.objects.filter(id__in=ids)
        for obj in qs:
            if exist_secret:
                obj.secret = secret
            post_save.send(obj.__class__, instance=obj, created=False)


class VaultManagerMixin(models.Manager):

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        objs = super().bulk_create(objs, batch_size=batch_size, ignore_conflicts=ignore_conflicts)
        for obj in objs:
            post_save.send(obj.__class__, instance=obj, created=True)
        return objs

    def bulk_update(self, objs, batch_size=None, ignore_conflicts=False):
        objs = super().bulk_update(objs, batch_size=batch_size, ignore_conflicts=ignore_conflicts)
        for obj in objs:
            post_save.send(obj.__class__, instance=obj, created=False)
        return objs
