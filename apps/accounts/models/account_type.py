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
    fields_definition = models.JSONField(default=list)
    is_builtin = models.BooleanField(default=False, verbose_name=_('Built-in'))
    comment = models.TextField(null=True, blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name

    def construct_serializer_class_for_fields_definition(self):
        from rest_framework import serializers
        fields = self._construct_serializer_class_fields()
        serializer_class = type(
            'AccountTypeFieldsDefinitionSerializer', (serializers.Serializer, ), fields
        )
        return serializer_class

    def _construct_serializer_class_fields(self):
        from ..const import FieldDefinitionTypeChoices
        fields = {}
        for field_definition in copy.deepcopy(self.fields_definition):
            name = field_definition.pop('name')
            tp = field_definition.pop('type')
            field_class = FieldDefinitionTypeChoices.get_serializer_field_class(tp=tp)
            # Integer type
            if tp == FieldDefinitionTypeChoices.int:
                default = field_definition.get('default')
                if isinstance(default, str) and default.isdigit():
                    field_definition['default'] = int(default)
            # Some combinations of keyword arguments do not make sense.
            if field_definition.get('write_only', False):
                field_definition.pop('read_only', None)
            if field_definition.get('read_only', False):
                field_definition.pop('required', None)
            if field_definition.get('required', False):
                field_definition.pop('default', None)

            fields[name] = field_class(**field_definition)
        return fields

    @classmethod
    def initial_builtin_type(cls):
        pass
