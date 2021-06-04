# -*- coding: utf-8 -*-
#

from django.db import models, transaction
from django.db.models import Max
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from simple_history.models import HistoricalRecords
from orgs.mixins.models import OrgManager
from .base import BaseUser

__all__ = ['AuthBook']


class AuthBookQuerySet(models.QuerySet):
    def delete(self):
        for instance in self:
            instance.delete()


class AuthBookManager(OrgManager):
    pass


class BaseAuthBook(BaseUser):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    system_user = models.ForeignKey('assets.SystemUser', on_delete=models.DO_NOTHING, db_constraint=False, null=True)
    version = models.IntegerField(default=1, verbose_name=_('Version'))

    class Meta:
        abstract = True


class AuthBookHistory(BaseAuthBook):
    authbook = models.ForeignKey('assets.AuthBook', db_constraint=False, on_delete=models.DO_NOTHING)
    date_joined = models.DateTimeField(auto_now_add=True, null=True, verbose_name=_("Date joined"))

    @classmethod
    def create_history(cls, authbook):
        history = cls()
        for attr in authbook.__dict__:
            setattr(history, attr, getattr(authbook, attr))
        history.authbook = authbook
        history.date_joined = timezone.now()
        history.save()


class AuthBook(BaseAuthBook):
    is_latest = models.BooleanField(default=False, verbose_name=_('Latest version'))

    objects = AuthBookManager.from_queryset(AuthBookQuerySet)()
    backend = "db"
    # 用于system user和admin_user的动态设置
    _connectivity = None
    CONN_CACHE_KEY = "ASSET_USER_CONN_{}"

    class Meta:
        verbose_name = _('AuthBook')

    def get_related_assets(self):
        return [self.asset]

    def generate_id_with_asset(self, asset):
        return self.id

    @classmethod
    def get_max_version(cls, username, asset):
        version_max = cls.objects.filter(username=username, asset=asset) \
            .aggregate(Max('version'))
        version_max = version_max['version__max'] or 0
        return version_max

    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)
        instance.save()
        return instance

    def save(self):
        username = self.username
        asset = self.asset

        with transaction.atomic():
            # 使用select_for_update限制并发创建相同的username、asset条目
            instances = AuthBook.objects.select_for_update().filter(username=username, asset=asset)
            history_versions = AuthBookHistory.objects.filter(username=username, asset=asset).values_list('version', flat=True)
            instance_versions = list(instances.values_list('version', flat=True))
            instance_versions.extend(history_versions)
            instance_versions.append(1)
            max_version = max(instance_versions)

            for instance in instances:
                AuthBookHistory.create_history(instance)
                instance.delete()

            self.version = max_version + 1
            return super().save()

    def delete(self, using=None, keep_parents=False):
        with transaction.atomic():
            AuthBookHistory.create_history(self)
            return super().delete(using=using, keep_parents=keep_parents)

    @property
    def connectivity(self):
        return self.get_asset_connectivity(self.asset)

    @property
    def keyword(self):
        return '{}_#_{}'.format(self.username, str(self.asset.id))

    @property
    def hostname(self):
        return self.asset.hostname

    @property
    def ip(self):
        return self.asset.ip

    def __str__(self):
        return '{}@{}'.format(self.username, self.asset)

