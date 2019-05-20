# coding: utf-8
#

import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _

from orgs.mixins import OrgModelMixin
from common.fields.model import EncryptJsonDictTextField

from .. import const


__all__ = [
    'RemoteApp',
]


class RemoteApp(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset')
    )
    system_user = models.ForeignKey(
        'assets.SystemUser', on_delete=models.CASCADE,
        verbose_name=_('System user')
    )
    type = models.CharField(
        default=const.REMOTE_APP_TYPE_CHROME,
        choices=const.REMOTE_APP_TYPE_CHOICES,
        max_length=128, verbose_name=_('App type')
    )
    path = models.CharField(
        max_length=128, blank=False, null=False,
        verbose_name=_('App path')
    )
    params = EncryptJsonDictTextField(
        max_length=4096, default={}, blank=True, null=True,
        verbose_name=_('Parameters')
    )
    created_by = models.CharField(
        max_length=32, null=True, blank=True, verbose_name=_('Created by')
    )
    date_created = models.DateTimeField(
        auto_now_add=True, null=True, blank=True, verbose_name=_('Date created')
    )
    comment = models.TextField(
        max_length=128, default='', blank=True, verbose_name=_('Comment')
    )

    class Meta:
        verbose_name = _("RemoteApp")
        unique_together = [('org_id', 'name')]
        ordering = ('name', )

    def __str__(self):
        return self.name

    @property
    def parameters(self):
        """
        返回Guacamole需要的RemoteApp配置参数信息中的parameters参数
        """
        _parameters = list()
        _parameters.append(self.type)
        path = '\"%s\"' % self.path
        _parameters.append(path)
        for field in const.REMOTE_APP_TYPE_MAP_FIELDS[self.type]:
            value = self.params.get(field['name'])
            if value is None:
                continue
            _parameters.append(value)
        _parameters = ' '.join(_parameters)
        return _parameters

    @property
    def asset_info(self):
        return {
            'id': self.asset.id,
            'hostname': self.asset.hostname
        }

    @property
    def system_user_info(self):
        return {
            'id': self.system_user.id,
            'name': self.system_user.name
        }
