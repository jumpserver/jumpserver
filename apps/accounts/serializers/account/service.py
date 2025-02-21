from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import IntegrationApplication
from acls.serializers.rules import ip_group_child_validator, ip_group_help_text
from common.serializers.fields import JSONManyToManyField


class IntegrationApplicationSerializer(serializers.ModelSerializer):
    accounts = JSONManyToManyField(label=_('Account'))
    ip_group = serializers.ListField(
        default=['*'], label=_('Access IP'), help_text=ip_group_help_text,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator])
    )

    class Meta:
        model = IntegrationApplication
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['logo', 'accounts']
        fields = fields_small + [
            'date_last_used', 'date_created', 'date_updated',
            'ip_group', 'accounts_amount', 'comment', 'is_active'
        ]
        extra_kwargs = {
            'comment': {'label': _('Comment')},
            'name': {'label': _('Name')},
            'is_active': {'default': True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request_method = self.context.get('request').method
        if request_method == 'PUT':
            self.fields['logo'].required = False


class IntegrationAccountSecretSerializer(serializers.Serializer):
    asset = serializers.CharField(required=False, allow_blank=True)
    asset_id = serializers.UUIDField(required=False, allow_null=True)
    account = serializers.CharField(required=False, allow_blank=True)
    account_id = serializers.UUIDField(required=False, allow_null=True)

    @staticmethod
    def _valid_at_least_one(attrs, fields):
        if not any(attrs.get(field) for field in fields):
            raise serializers.ValidationError(
                f"At least one of the following fields must be provided: {', '.join(fields)}."
            )

    def validate(self, attrs):
        if attrs.get('account_id'):
            return attrs

        self._valid_at_least_one(attrs, ['asset', 'asset_id'])
        self._valid_at_least_one(attrs, ['account', 'account_id'])
        return attrs
