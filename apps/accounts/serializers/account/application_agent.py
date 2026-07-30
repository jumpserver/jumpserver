from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from accounts.const import (
    ApplicationAgentEventStatus, ApplicationAgentStatus, ApplicationSwitchStatus,
)
from accounts.models import (
    Account, ApplicationAccountBinding, ApplicationAccountSwitch,
    ApplicationAccountSwitchItem,
    IntegrationApplication, IntegrationApplicationAgent,
    IntegrationApplicationAgentEvent,
)
from accounts.notifications import ApplicationAccountSwitchMessage
from common.serializers import CommonModelSerializer
from common.serializers.fields import ObjectRelatedField


def publish_message(user, title, detail):
    if not user:
        return
    try:
        ApplicationAccountSwitchMessage(user, title, detail).publish_async()
    except Exception:
        # Notification configuration must not affect credential delivery.
        pass


def publish_messages(users, title, detail):
    for user in users:
        publish_message(user, title, detail)


def account_credential(account, credential_id):
    if settings.SECURITY_DISABLE_VIEW_SECRET:
        raise PermissionDenied(_('Viewing account secret is disabled.'))
    return {
        'credential_id': str(credential_id),
        'account_id': str(account.id),
        'username': account.username,
        'secret': account.secret,
        'secret_type': account.secret_type,
        'version': account.version,
    }


class IntegrationApplicationAgentSerializer(CommonModelSerializer):
    status = serializers.SerializerMethodField(label=_('Status'))

    class Meta:
        model = IntegrationApplicationAgent
        fields = [
            'id', 'status', 'hostname', 'platform', 'version',
            'last_seen', 'error',
        ]

    @staticmethod
    def get_status(instance):
        status = ApplicationAgentStatus(instance.status)
        return {'value': status.value, 'label': status.label}


class ApplicationAccountBindingSerializer(CommonModelSerializer):
    account = ObjectRelatedField(
        source='current_account', read_only=True, attrs=('id', 'name', 'username')
    )
    asset = ObjectRelatedField(
        source='current_account.asset', read_only=True,
        attrs=('id', 'name', 'address')
    )

    class Meta:
        model = ApplicationAccountBinding
        fields = ['id', 'account', 'asset']


class ApplicationAccountSwitchItemSerializer(CommonModelSerializer):
    credential_id = serializers.UUIDField(source='binding_id', read_only=True)
    application = ObjectRelatedField(
        source='binding.application', read_only=True, attrs=('id', 'name')
    )

    class Meta:
        model = ApplicationAccountSwitchItem
        fields = [
            'id', 'credential_id', 'application', 'status', 'error',
            'date_delivered', 'date_confirmed', 'date_updated',
        ]


class ApplicationAccountSwitchSerializer(CommonModelSerializer):
    source_account = ObjectRelatedField(read_only=True, attrs=('id', 'name', 'username'))
    target_account = ObjectRelatedField(read_only=True, attrs=('id', 'name', 'username'))
    items = ApplicationAccountSwitchItemSerializer(many=True, read_only=True)

    class Meta:
        model = ApplicationAccountSwitch
        fields = [
            'id', 'source_account', 'target_account', 'status', 'items',
            'created_by', 'date_created', 'date_updated', 'date_finished', 'comment',
        ]


class ApplicationAccountSwitchCreateSerializer(serializers.Serializer):
    source_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects, label=_('Source account')
    )
    target_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects, label=_('Target account')
    )
    comment = serializers.CharField(required=False, allow_blank=True, label=_('Comment'))

    def validate(self, attrs):
        source = attrs['source_account']
        target = attrs['target_account']
        if source == target:
            raise serializers.ValidationError({
                'target_account': _('Target account must differ from source account.')
            })
        if source.asset_id != target.asset_id:
            raise serializers.ValidationError({
                'target_account': _('Target account must belong to the same asset.')
            })
        return attrs

    def create(self, validated_data):
        switch = ApplicationAccountSwitch.start(
            user=self.context['request'].user, **validated_data
        )
        self.notify_owners(switch)
        return switch

    @staticmethod
    def notify_owners(switch):
        owners = {
            item.binding.application.owner_id: item.binding.application.owner
            for item in switch.items.select_related('binding__application__owner')
            if item.binding.application.owner
        }
        title = _('Application account switch started')
        detail = _(
            'Switch account {source} to {target}. Please reload the application after delivery.'
        ).format(source=switch.source_account.name, target=switch.target_account.name)
        transaction.on_commit(
            lambda: publish_messages(owners.values(), title, detail)
        )


class ApplicationAccountSwitchConfirmSerializer(serializers.Serializer):
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=ApplicationAccountSwitchItem.objects, source='item'
    )

    def validate_item_id(self, item):
        if item.switch_id != self.instance.id:
            raise serializers.ValidationError(
                _('The item does not belong to this switch task.')
            )
        user = self.context['request'].user
        is_owner = item.binding.application.owner_id == user.id
        if not is_owner and not user.has_perm('accounts.change_integrationapplication'):
            raise PermissionDenied(_('Only the application owner or an administrator can confirm.'))
        return item

    def update(self, instance, validated_data):
        return validated_data['item'].confirm(self.context['request'].user)


class AgentIdentitySerializer(serializers.Serializer):
    agent_id = serializers.UUIDField(label=_('Agent ID'))

    def validate_agent_id(self, agent_id):
        agent = getattr(self.context['request'].user, 'agent', None)
        if not agent or agent.id != agent_id:
            raise PermissionDenied(_('Agent identity does not match this application.'))
        self.agent = agent
        return agent_id


class AgentRegisterSerializer(serializers.Serializer):
    agent_id = serializers.UUIDField(label=_('Agent ID'))
    hostname = serializers.CharField(max_length=255, allow_blank=True, required=False)
    platform = serializers.CharField(max_length=64, allow_blank=True, required=False)
    version = serializers.CharField(max_length=64, allow_blank=True, required=False)

    @transaction.atomic
    def create(self, validated_data):
        authenticated_application = self.context['request'].user
        application = IntegrationApplication.objects.select_for_update().get(
            pk=authenticated_application.pk
        )
        if application.secret != authenticated_application.secret:
            raise PermissionDenied(_('Application credentials have been reset.'))
        if (application.accounts.value or {}).get('type') != 'ids':
            raise serializers.ValidationError({
                'agent_id': _(
                    'Application Agent credentials must use explicitly selected accounts.'
                )
            })
        agent = getattr(application, 'agent', None)
        agent_id = validated_data.pop('agent_id')
        if agent and agent.id != agent_id:
            raise PermissionDenied(_('Another Agent is already registered for this application.'))
        if not agent:
            if IntegrationApplicationAgent.objects.filter(pk=agent_id).exists():
                raise serializers.ValidationError({
                    'agent_id': _('This Agent ID is already registered.')
                })
            agent = IntegrationApplicationAgent(
                id=agent_id, application=application, org_id=application.org_id
            )
        for field in ('hostname', 'platform', 'version'):
            setattr(agent, field, validated_data.get(field, ''))
        agent.last_seen = timezone.now()
        agent.error = ''
        try:
            with transaction.atomic():
                agent.save()
        except IntegrityError:
            raise serializers.ValidationError({
                'agent_id': _('This Agent ID is already registered.')
            })
        application.date_last_used = agent.last_seen
        application.save(update_fields=['date_last_used', 'date_updated'])
        return agent


class AgentRegisterResultSerializer(serializers.Serializer):
    application = serializers.SerializerMethodField()
    agent_id = serializers.UUIDField(source='id')
    credential_dir_rule = serializers.SerializerMethodField()
    credentials = serializers.SerializerMethodField()

    @staticmethod
    def get_application(agent):
        return {'id': agent.application_id, 'name': agent.application.name}

    @staticmethod
    def get_credential_dir_rule(agent):
        return '<credential_dir>/<credential_alias>.json'

    @staticmethod
    def get_credentials(agent):
        active_items = ApplicationAccountSwitchItem.objects.filter(
            binding__application=agent.application,
            switch__status__in=(
                ApplicationSwitchStatus.RUNNING,
                ApplicationSwitchStatus.WAITING_CONFIRMATION,
                ApplicationSwitchStatus.ROLLING_BACK,
            ),
        ).select_related('switch', 'switch__source_account', 'switch__target_account')
        desired_accounts = {
            item.binding_id: (
                item.switch.source_account
                if item.switch.status == ApplicationSwitchStatus.ROLLING_BACK
                else item.switch.target_account
            )
            for item in active_items
        }
        bindings = agent.application.account_bindings.filter(
            current_account__is_active=True
        ).select_related('current_account')
        return [
            account_credential(
                desired_accounts.get(binding.id, binding.current_account), binding.id
            )
            for binding in bindings
        ]


class AgentHeartbeatSerializer(AgentIdentitySerializer):
    def create(self, validated_data):
        return self.agent.touch()


class AgentEventSerializerMixin:
    def validate_event_id(self, event):
        if event.item.binding.application_id != self.context['request'].user.id:
            raise PermissionDenied(_('The event does not belong to this application.'))
        return event


class AgentEventCredentialQuerySerializer(
    AgentEventSerializerMixin, serializers.Serializer
):
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=IntegrationApplicationAgentEvent.objects.filter(
            status=ApplicationAgentEventStatus.PENDING
        ), source='event', label=_('Event')
    )

    def validate(self, attrs):
        if not getattr(self.context['request'].user, 'agent', None):
            raise PermissionDenied(_('No Agent is registered for this application.'))
        return super().validate(attrs)

    @property
    def credential(self):
        event = self.validated_data['event']
        return account_credential(
            event.desired_account, event.item.binding_id
        )


class AgentEventReportSerializer(AgentEventSerializerMixin, AgentIdentitySerializer):
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=IntegrationApplicationAgentEvent.objects,
        source='event', label=_('Event')
    )
    success = serializers.BooleanField(label=_('Success'))
    error = serializers.CharField(required=False, allow_blank=True, max_length=2048)

    def create(self, validated_data):
        event, self.duplicate = validated_data['event'].report(
            validated_data['success'], validated_data.get('error', '')
        )
        if not self.duplicate:
            self.notify_owner(event, validated_data['success'])
        return event

    @staticmethod
    def notify_owner(event, success):
        result = _('succeeded') if success else _('failed')
        detail = _('Credential delivery for {app}/{account} {result}.').format(
            app=event.item.binding.application.name,
            account=event.desired_account.name,
            result=result,
        )
        publish_message(
            event.item.binding.application.owner,
            _('Application credential delivery'), detail
        )
