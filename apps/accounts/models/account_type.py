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

    def get_fields_definition_serializer(self):
        from rest_framework import serializers
        from ..const import FieldDefinitionTypeChoices
        serializer_fields = {}
        fields_definition = copy.deepcopy(self.fields_definition)
        for field_definition in fields_definition:
            field_name = field_definition.pop('name')
            required = field_definition.pop('required', False)
            if required:
                field_definition.pop('default')
            tp = field_definition.pop('type')
            serializer_field_class = FieldDefinitionTypeChoices.get_serializer_field_class(tp)
            serializer_fields[field_name] = serializer_field_class(**field_definition)
        cls_name = 'AccountTypeFieldsDefinitionSerializer'
        return type(cls_name, (serializers.Serializer, ), serializer_fields)()

    @classmethod
    def initial_builtin_type(cls):
        pass
