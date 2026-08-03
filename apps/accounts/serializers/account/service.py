from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import ApplicationAgentStatus, ApplicationSwitchStatus
from accounts.models import (
    Account, ApplicationAccountBinding, ApplicationAccountSwitch,
    IntegrationApplication,
)
from acls.serializers.rules import ip_group_child_validator, ip_group_help_text
from common.db.fields import RelatedManager
from common.serializers.fields import JSONManyToManyField
from common.serializers.fields import ObjectRelatedField
from common.utils import random_string
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from users.models import User

from .application_agent import (
    ApplicationAccountBindingSerializer, IntegrationApplicationAgentSerializer,
)


class IntegrationApplicationSerializer(BulkOrgResourceModelSerializer):
    owner = ObjectRelatedField(
        queryset=User.objects, attrs=('id', 'name', 'username'), label=_('Owner')
    )
    accounts = JSONManyToManyField(label=_('Account'))
    agent = serializers.SerializerMethodField(label=_('Agent'))
    account_bindings = ApplicationAccountBindingSerializer(many=True, read_only=True)
    ip_group = serializers.ListField(
        default=['*'], label=_('Access IP'), help_text=ip_group_help_text,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator])
    )

    class Meta:
        model = IntegrationApplication
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['logo', 'owner', 'accounts']
        fields = fields_small + [
            'date_last_used', 'date_created', 'date_updated',
            'ip_group', 'accounts_amount', 'account_bindings', 'agent',
            'comment', 'is_active'
        ]
        extra_kwargs = {
            'comment': {'label': _('Comment')},
            'name': {'label': _('Name')},
            'accounts_amount': {'label': _('Accounts amount')},
            'is_active': {'default': True},
            'logo': {'required': False},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get('logo'):
            data['logo'] = static('img/logo.png')
        return data

    @classmethod
    def setup_eager_loading(cls, queryset):
        return queryset.select_related('owner', 'agent').prefetch_related(
            'account_bindings__current_account__asset'
        )

    @staticmethod
    def get_agent(instance):
        agent = getattr(instance, 'agent', None)
        if agent:
            return IntegrationApplicationAgentSerializer(agent).data
        status = ApplicationAgentStatus.UNREGISTERED
        return {
            'id': None,
            'status': {'value': status.value, 'label': status.label},
            'hostname': '',
            'platform': '',
            'version': '',
            'last_seen': None,
            'error': '',
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        application = self.instance
        accounts = attrs.get('accounts')
        if not application or accounts is None:
            return attrs
        if getattr(application, 'agent', None) and accounts.get('type') != 'ids':
            raise serializers.ValidationError({
                'accounts': _(
                    'Application Agent credentials must use explicitly selected accounts.'
                )
            })
        account_ids = set(
            Account.objects.filter(
                *RelatedManager.get_to_filter_qs(accounts, Account)
            ).values_list('id', flat=True)
        )
        active_account_ids = set(ApplicationAccountSwitch.objects.filter(
            items__binding__application=application,
            status__in=(
                ApplicationSwitchStatus.RUNNING,
                ApplicationSwitchStatus.WAITING_CONFIRMATION,
                ApplicationSwitchStatus.ROLLING_BACK,
            ),
        ).values_list('items__binding__current_account_id', flat=True))
        if active_account_ids - account_ids:
            raise serializers.ValidationError({
                'accounts': _('Accounts in an active switch task cannot be removed.')
            })
        return attrs

    def create(self, validated_data):
        instance = super().create(validated_data)
        ApplicationAccountBinding.sync_application(instance)
        instance.refresh_secret()
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        ApplicationAccountBinding.sync_application(instance)
        return instance


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
