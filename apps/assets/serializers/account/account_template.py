from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from assets.models import AccountTemplate
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from assets.serializers.base import AuthSerializerMixin
from .common import BaseAccountSerializer


class AccountTemplateSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    class Meta:
        model = AccountTemplate
        fields_mini = ['id', 'privileged', 'username', 'name']
        fields_write_only = BaseAccountSerializer.Meta.fields_write_only
        fields_other = BaseAccountSerializer.Meta.fields_other
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


class AccountTemplateSerializerMixin(serializers.ModelSerializer):
    account_template = serializers.UUIDField(
        required=False, allow_null=True, write_only=True,
        label=_('Account template')
    )

    @staticmethod
    def validate_account_template(value):
        AccountTemplate.objects.get_or_create()
        model = AccountTemplate
        try:
            return model.objects.get(id=value)
        except AccountTemplate.DoesNotExist:
            raise serializers.ValidationError(_('Account template not found'))

    @staticmethod
    def replace_attrs(account_template: AccountTemplate, attrs: dict):
        exclude_fields = [
            '_state', 'org_id', 'date_verified', 'id', 'date_created', 'date_updated', 'created_by'
        ]
        template_attrs = {k: v for k, v in account_template.__dict__.items() if k not in exclude_fields}
        for k, v in template_attrs.items():
            attrs.setdefault(k, v)

    def _validate(self, attrs):
        account_template = attrs.pop('account_template', None)
        if account_template:
            self.replace_attrs(account_template, attrs)
        else:
            AccountTemplateSerializer.validate_required(attrs)
        return attrs




