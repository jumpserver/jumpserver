# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from assets.models import SystemUser
from applications.models import Application
from applications.serializers import ApplicationSerializerMixin

__all__ = [
    'ApplicationGrantedSerializer', 'ApplicationSystemUserSerializer'
]


class ApplicationSystemUserSerializer(serializers.ModelSerializer):
    """
    查看授权的应用系统用户的数据结构，这个和SystemUserSerializer不同，字段少
    """
    class Meta:
        model = SystemUser
        only_fields = (
            'id', 'name', 'username', 'priority', 'protocol', 'login_mode'
        )
        fields = list(only_fields)
        read_only_fields = fields


class ApplicationGrantedSerializer(ApplicationSerializerMixin, serializers.ModelSerializer):
    """
    被授权应用的数据结构
    """
    category_display = serializers.ReadOnlyField(source='get_category_display', label=_('Category'))
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type'))

    class Meta:
        model = Application
        only_fields = [
            'id', 'name', 'domain', 'category', 'type', 'attrs', 'comment', 'org_id'
        ]
        fields = only_fields + ['category_display', 'type_display', 'org_name']
        read_only_fields = fields
