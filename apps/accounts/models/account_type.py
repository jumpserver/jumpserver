import copy
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin


__all__ = ['AccountType']


class AccountType(CommonModelMixin, models.Model):
    """ 账号类型: 用来标识此类型账号所需要的其他附加字段 (全局通用) """
    class CategoryChoices(models.TextChoices):
        os = 'operating_system', 'Operating System'
        cloud = 'cloud_service', 'Cloud Service'
        website = 'website', ' Website'
        db = 'database', 'Database'
        application = 'application', 'Application'
        network_device = 'network_device', 'Network Device'

    class SecretTypeChoices(models.TextChoices):
        ssh_keys = 'ssh_keys', 'SSH Keys'
        password = 'password', 'Password'
        cert = 'cert', 'Certificate'
        token = 'token', 'Token'
        text = 'text', 'Text'

    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    category = models.CharField(
        max_length=128, default=CategoryChoices.os, choices=CategoryChoices.choices,
        verbose_name=_('Category')
    )
    # ssh / rdp / telnet / vnc
    # https / http
    # mysql
    protocol = models.CharField(max_length=128, verbose_name=_('Protocol'))
    secret_type = models.CharField(
        max_length=128, default=SecretTypeChoices.password, choices=SecretTypeChoices.choices,
        verbose_name=_('Secret type')
    )
    # [{'name': '', 'type': '', 'read_only': '', 'label': '', ...}, {}, {}]
    properties = models.JSONField(default=list)
    is_builtin = models.BooleanField(default=False, verbose_name=_('Built-in'))
    comment = models.TextField(null=True, blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name

    def construct_serializer_class_for_properties(self):
        from rest_framework import serializers
        fields = self._construct_serializer_class_fields()
        serializer_class = type(
            'AccountTypePropertiesSerializer', (serializers.Serializer, ), fields
        )
        return serializer_class

    def _construct_serializer_class_fields(self):
        from ..const import PropertyTypeChoices
        fields = {}
        for _property in copy.deepcopy(self.properties):
            name = _property.pop('name')
            tp = _property.pop('type')
            default = _property.get('default')
            field_class = PropertyTypeChoices.get_serializer_field_class(tp=tp)
            # int type
            if tp == PropertyTypeChoices.int:
                if isinstance(default, str) and default.isdigit():
                    _property['default'] = int(default)
            # str type
            if tp == PropertyTypeChoices.str:
                _property['max_length'] = 1024
            if tp == PropertyTypeChoices.bool:
                _property['default'] = default in ['true', True, '1']
            # Some combinations of keyword arguments do not make sense.
            if _property.get('write_only', False):
                _property.pop('read_only', None)
            if _property.get('read_only', False):
                _property.pop('required', None)
            if _property.get('required', False):
                _property.pop('default', None)

            fields[name] = field_class(**_property)
        return fields

    @classmethod
    def initial_builtin_type(cls):
        pass
