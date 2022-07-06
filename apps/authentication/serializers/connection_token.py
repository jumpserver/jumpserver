from rest_framework import serializers
from django.conf import settings
from datetime import datetime, timedelta

from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from authentication.models import ConnectionToken
from common.utils import pretty_string
from common.utils.random import random_string
from applications.models import Application
from assets.models import Asset


__all__ = ['ConnectionTokenSerializer']


class ConnectionTokenSerializer(OrgResourceModelSerializerMixin):

    class Meta:
        model = ConnectionToken
        fields_mini = ['id', 'type']
        fields_small = fields_mini + [
            'secret',
            'date_expired',
            'date_created', 'date_updated', 'created_by', 'updated_by',
            'org_id', 'org_name',
        ]
        fields_fk = [
            'user', 'system_user', 'asset', 'application',
        ]
        read_only_fields = [
            'user_display', 'system_user_display', 'asset_display', 'application_display',
        ]
        fields = fields_small + fields_fk + read_only_fields

    def validate(self, attrs):
        fields_attrs = self.construct_internal_fields_attrs(attrs)
        attrs.update(fields_attrs)
        return attrs

    @staticmethod
    def construct_internal_fields_attrs(attrs):
        user = attrs.get('user') or ''
        system_user = attrs.get('system_user') or ''
        asset = attrs.get('asset') or ''
        application = attrs.get('application') or ''
        secret = attrs.get('secret') or random_string(64)
        date_expired = attrs.get('date_expired') or ConnectionToken.get_default_date_expired()

        if isinstance(asset, Asset):
            tp = ConnectionToken.Type.asset
            org_id = asset.org_id
        elif isinstance(application, Application):
            tp = ConnectionToken.Type.application
            org_id = application.org_id
        else:
            raise serializers.ValidationError(_('Asset or application required'))

        return {
            'type': tp,
            'secret': secret,
            'date_expired': date_expired,
            'user_display': pretty_string(str(user), max_length=128),
            'system_user_display': pretty_string(str(system_user), max_length=128),
            'asset_display': pretty_string(str(asset), max_length=128),
            'application_display': pretty_string(str(application), max_length=128),
            'org_id': org_id,
        }
