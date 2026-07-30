import json
import time

from django.db import transaction
from django.http import StreamingHttpResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from accounts import serializers
from accounts.const import ApplicationAgentEventStatus
from accounts.models import (
    ApplicationAccountBinding, ApplicationAccountSwitch, IntegrationApplication,
    IntegrationApplicationAgentEvent,
)
from authentication.permissions import IsValidUser
from common.api import JMSGenericViewSet
from common.db.utils import close_old_connections
from orgs.mixins.api import OrgGenericViewSet


class EventStreamRenderer(JSONRenderer):
    media_type = 'text/event-stream'
    format = 'event-stream'


def stream_agent_events(application_id):
    sent = set()
    deadline = time.monotonic() + 55
    while time.monotonic() < deadline:
        close_old_connections()
        events = IntegrationApplicationAgentEvent.objects.filter(
            item__binding__application_id=application_id,
            status=ApplicationAgentEventStatus.PENDING,
        ).select_related('item').order_by('date_created')
        for event in events:
            if event.id in sent:
                continue
            data = json.dumps(event.as_payload())
            yield f'id: {event.id}\nevent: credential.change\ndata: {data}\n\n'
            sent.add(event.id)
        yield ': heartbeat\n\n'
        time.sleep(5)


class ApplicationAccountSwitchViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.CreateModelMixin, OrgGenericViewSet,
):
    model = ApplicationAccountSwitch
    perm_model = IntegrationApplication
    serializer_classes = {
        'default': serializers.ApplicationAccountSwitchSerializer,
        'create': serializers.ApplicationAccountSwitchCreateSerializer,
        'confirm': serializers.ApplicationAccountSwitchConfirmSerializer,
    }
    filterset_fields = ['source_account_id', 'target_account_id', 'status']
    search_fields = [
        'source_account__name', 'source_account__username',
        'target_account__name', 'target_account__username',
    ]
    rbac_perms = {
        'create': 'accounts.change_integrationapplication',
        'rollback': 'accounts.change_integrationapplication',
        'end': 'accounts.change_integrationapplication',
        'confirm': 'accounts.view_integrationapplication',
        'credentials': 'accounts.view_integrationapplication',
    }

    @action(['GET'], detail=False)
    def credentials(self, request, *args, **kwargs):
        bindings = ApplicationAccountBinding.objects.filter(
            application__agent__isnull=False,
            application__is_active=True,
            current_account__is_active=True,
        ).select_related('application', 'current_account__asset').order_by(
            'current_account__name', 'application__name'
        )
        credentials = {}
        for binding in bindings:
            account = binding.current_account
            credential = credentials.setdefault(str(account.id), {
                'account': {
                    'id': str(account.id),
                    'name': account.name,
                    'username': account.username,
                },
                'asset': {
                    'id': str(account.asset_id),
                    'name': account.asset.name,
                    'address': account.asset.address,
                },
                'bindings': [],
            })
            credential['bindings'].append({
                'credential_id': str(binding.id),
                'application': {
                    'id': str(binding.application_id),
                    'name': binding.application.name,
                },
            })
        return Response(list(credentials.values()))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        switch = serializer.save()
        data = serializers.ApplicationAccountSwitchSerializer(switch).data
        return Response(data, status=status.HTTP_201_CREATED)

    @action(['POST'], detail=True, permission_classes=[IsValidUser])
    def confirm(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        switch = serializer.save()
        return Response(serializers.ApplicationAccountSwitchSerializer(switch).data)

    @action(['POST'], detail=True)
    def rollback(self, request, *args, **kwargs):
        switch = self.get_object().rollback(request.user)
        return Response(self.get_serializer(switch).data)

    @action(['POST'], detail=True)
    def end(self, request, *args, **kwargs):
        switch = self.get_object().end(request.user)
        return Response(self.get_serializer(switch).data)


class RuntimeApplicationPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, IntegrationApplication) and request.user.is_active


class IntegrationApplicationAgentViewSet(JMSGenericViewSet):
    permission_classes = [RuntimeApplicationPermission]
    _ignore_rbac_permissions = True
    serializer_classes = {
        'register': serializers.AgentRegisterSerializer,
        'heartbeat': serializers.AgentHeartbeatSerializer,
        'credentials': serializers.AgentEventCredentialQuerySerializer,
        'reports': serializers.AgentEventReportSerializer,
        'events': serializers.AgentIdentitySerializer,
    }

    @action(['POST'], detail=False)
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            agent = serializer.save()
            data = serializers.AgentRegisterResultSerializer(agent).data
        return Response(data)

    @action(['POST'], detail=False)
    def heartbeat(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent = serializer.save()
        return Response({'server_time': agent.last_seen})

    @action(['GET'], detail=False)
    def credentials(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.credential)

    @action(['POST'], detail=False)
    def reports(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        return Response({
            'event_id': event.id,
            'status': event.status,
            'switch_status': event.item.switch.status,
            'duplicate': serializer.duplicate,
        })

    @action(['GET'], detail=False, renderer_classes=(EventStreamRenderer,))
    def events(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        response = StreamingHttpResponse(
            stream_agent_events(request.user.id), content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
