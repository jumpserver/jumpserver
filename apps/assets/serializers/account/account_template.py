from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from assets.models import AccountTemplate
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from assets.serializers.base import AuthValidateMixin
from .common import AccountFieldsSerializerMixin


class AccountTemplateSerializer(AuthValidateMixin, BulkOrgResourceModelSerializer):
    class Meta:
        model = AccountTemplate
        fields_mini = ['id', 'privileged', 'username']
        fields_write_only = AccountFieldsSerializerMixin.Meta.fields_write_only
        fields_other = AccountFieldsSerializerMixin.Meta.fields_other
        fields = fields_mini + fields_write_only + fields_other
        extra_kwargs = {
            'username': {'required': True},
            'private_key': {'write_only': True},
            'public_key': {'write_only': True},
        }

    def validate(self, attrs):
        attrs = self._validate_gen_key(attrs)
        return attrs

    @classmethod
    def validate_required(cls, attrs):
        required_field_dict = {}
        error = _('This field is required.')
        for k, v in cls().fields.items():
            if v.required and k not in attrs:
                required_field_dict[k] = error
        if not required_field_dict:
            return
        raise serializers.ValidationError(required_field_dict)

