# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _

from assets.models import BaseAccount
from assets.serializers.base import AuthValidateMixin
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

__all__ = ['BaseAccountSerializer']


class BaseAccountSerializer(AuthValidateMixin, BulkOrgResourceModelSerializer):
    class Meta:
        model = BaseAccount
        fields_mini = ['id', 'name', 'username']
        fields_small = fields_mini + [
            'secret_type', 'secret', 'has_secret', 'passphrase',
            'privileged', 'is_active', 'specific',
        ]
        fields_other = ['created_by', 'date_created', 'date_updated', 'comment']
        fields = fields_small + fields_other
        read_only_fields = [
            'has_secret', 'specific',
            'date_verified', 'created_by', 'date_created',
        ]
        extra_kwargs = {
            'specific': {'label': _('Specific')},
        }
