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

    def construct_serializer_cls_by_fields_definition(self):
        from rest_framework import serializers
        from ..const import FieldDefinitionTypeChoices
        fields_definition = copy.deepcopy(self.fields_definition)

        serializer_fields = {}
        for field_kwargs in fields_definition:
            field_type = field_kwargs.pop('type', None)
            # default
            field_default = field_kwargs.get('default', '')
            if field_type == FieldDefinitionTypeChoices.integer:
                if field_default and field_default.isdigit():
                    field_kwargs['default'] = int(field_default)
            # Some combinations of keyword arguments do not make sense.
            if field_kwargs.get('write_only', False):
                field_kwargs.pop('read_only', None)
            if field_kwargs.get('read_only', False):
                field_kwargs.pop('required', None)
            if field_kwargs.get('required', False):
                field_kwargs.pop('default', None)
            field_class = FieldDefinitionTypeChoices.get_serializer_field_class(field_type)
            field_name = field_kwargs.pop('name')
            serializer_fields[field_name] = field_class(**field_kwargs)
        cls_name = 'AccountTypeFieldsDefinitionSerializer'
        serializer_class = type(cls_name, (serializers.Serializer, ), serializer_fields)
        return serializer_class

    @classmethod
    def initial_builtin_type(cls):
        pass
