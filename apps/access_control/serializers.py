# -*- coding: utf-8 -*-
#
from IPy import IP
from rest_framework.exceptions import ValidationError
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .models import AccessControl


class LoginPolicySerializer(BulkOrgResourceModelSerializer):

    class Meta:
        model = AccessControl
        fields = ['id', 'name', 'ips', 'date_from', 'date_to', 'users']
        extra_kwargs = {
            'users': {'required': False, 'allow_empty': True}
        }

    def validate_ips(self, value: str):
        for ip in value.split(','):
            try:
                IP(ip.strip())
            except ValueError as e:
                raise ValidationError(e)
        return value
