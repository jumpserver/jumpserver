from uuid import UUID

from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _, get_language
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import serializers
from accounts.const import ApplicationEvent, AuditEvent
from accounts.filters import IntegrationApplicationFilterSet
from accounts.models import (
    ApplicationAudit, ApplicationWebhook, CredentialRotationEvent,
    IntegrationApplication,
)
from accounts.models.application import default_application_webhook_template
from accounts.webhooks import (
    WebhookValidationError, render_webhook_template, sample_webhook_context,
    webhook_template_variables,
)
from accounts.credential_client.audit import record
from accounts.credential_client.access_log import record_access
from accounts.mixins import ApplicationAuditMixin
from authentication.permissions import UserConfirmation, ConfirmType
from common.exceptions import JMSException
from common.utils import get_request_ip
from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission


class IntegrationApplicationViewSet(ApplicationAuditMixin, OrgBulkModelViewSet):
    model = IntegrationApplication
    filterset_class = IntegrationApplicationFilterSet
    search_fields = ('name', 'comment')
    serializer_classes = {
        'default': serializers.IntegrationApplicationSerializer,
        'retrieve': serializers.IntegrationApplicationDetailSerializer,
    }
    rbac_perms = {
        'get_once_secret': 'accounts.change_integrationapplication',
        'reset_secret': 'accounts.change_integrationapplication',
        'get_sdks_info': 'accounts.view_integrationapplication',
        'credential_events': 'accounts.view_integrationapplication',
        'access_materials': 'accounts.change_integrationapplication',
        'send_event_options': 'accounts.change_integrationapplication',
        'send_event': 'accounts.change_integrationapplication',
        'manual_events': 'accounts.view_integrationapplication',
    }

    @action(['GET'], detail=True, url_path='send-event-options')
    def send_event_options(self, request, *args, **kwargs):
        from accounts.credential_client.commands import options
        return Response(options(self.get_object()))

    @action(['POST'], detail=True, url_path='send-event')
    def send_event(self, request, *args, **kwargs):
        from accounts.credential_client.commands import detail, send, SWITCH
        serializer = serializers.ApplicationCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data['event'] == SWITCH and not request.user.has_perm('accounts.change_applicationcredential'):
            raise PermissionDenied()
        application = self.get_object()
        self.start_audit(AuditEvent.COMMAND_REQUESTED, application=application)
        command = send(application, data, request.user.name)
        return Response(detail(command), status=201)

    @action(['GET'], detail=True, url_path='manual-events')
    def manual_events(self, request, *args, **kwargs):
        from accounts.credential_client.commands import detail
        try:
            limit = min(max(int(request.query_params.get('limit', 30)), 1), 100)
            offset = max(int(request.query_params.get('offset', 0)), 0)
        except (TypeError, ValueError):
            raise ValidationError(_('Invalid pagination parameters.'))
        commands = self.get_object().commands.select_related('source_event')
        if request.query_params.get('command_id'):
            try:
                commands = commands.filter(id=UUID(request.query_params['command_id']))
            except (TypeError, ValueError):
                raise ValidationError(_('Invalid command ID.'))
        return Response({'count': commands.count(), 'results': [detail(command) for command in commands[offset:offset + limit]]})

    @action(
        ['POST'], detail=True, url_path='access-materials',
        permission_classes=[RBACPermission, UserConfirmation.require(ConfirmType.MFA)],
    )
    def access_materials(self, request, *args, **kwargs):
        from accounts.credential_client.access import materials
        application = self.get_object()
        params = serializers.CredentialAccessWizardSerializer(
            data=request.data, context={'application': application},
        )
        params.is_valid(raise_exception=True)
        data = materials(application, params.validated_data, request.build_absolute_uri('/').rstrip('/'))
        record(AuditEvent.CONFIGURATION_UPDATED, application=application, summary='Generated application access materials.')
        response = Response(data)
        response['Cache-Control'] = 'no-store'
        return response

    @action(
        ['GET'], detail=False, url_path='sdks',
    )
    def get_sdks_info(self, request, *args, **kwargs):
        from accounts.credential_client.documentation import get_sdk_documentation
        sdk_language = request.query_params.get('language', 'python')
        return Response(get_sdk_documentation(sdk_language, get_language()))

    @action(['GET'], detail=True, url_path='credential-events')
    def credential_events(self, request, *args, **kwargs):
        from accounts.credential_rotation.cycles import event_account_context, event_account_data

        application = self.get_object()
        try:
            limit = min(max(int(request.query_params.get('limit', 30)), 1), 100)
            offset = max(int(request.query_params.get('offset', 0)), 0)
        except (TypeError, ValueError):
            raise ValidationError(_('Invalid pagination parameters.'))
        application_id = str(application.id)
        source_ids = ApplicationAudit.objects.filter(
            org_id=application.org_id, application_relations__application_id=application.id,
        ).values('id')
        events = CredentialRotationEvent.objects.filter(
            org_id=application.org_id, source_event_id__in=source_ids,
        ).order_by('-published_at', '-id')
        count = events.count()
        page = list(events.select_related('rotation')[offset:offset + limit])
        audits, accounts = event_account_data(page, application.org_id)
        results = []
        for event in page:
            audit = audits.get(event.source_event_id)
            recipients = [
                {
                    'instance_id': recipient['instance_id'],
                    'type': recipient['type'],
                    'publish_result': recipient['publish_result'],
                    'received_at': recipient['received_at'],
                    'status': recipient.get('status', 'pending'),
                    'finished_at': recipient.get('finished_at'),
                    'error_code': recipient.get('error_code', ''),
                    'account_id': recipient.get('account_id'),
                    'account_revision': recipient.get('account_revision'),
                    'fetched_at': recipient.get('fetched_at'),
                    'delivered_at': recipient.get('delivered_at'),
                }
                for recipient in event.recipients
                if recipient['application']['id'] == application_id
            ]
            results.append({
                'id': str(event.source_event_id),
                'event': event.event,
                'notification_enabled': event.notification_enabled,
                'operation_id': str(audit.operation_id) if audit and audit.operation_id else None,
                'result': audit.result if audit else '',
                'account_id': str(audit.account_id) if audit and audit.account_id else None,
                'published_at': event.published_at,
                'revision': event.revision,
                'rotation_id': str(event.rotation_id) if event.rotation_id else None,
                'credential_id': str(audit.credential_id) if audit and audit.credential_id else None,
                'credential': audit.credential if audit else '',
                'account': audit.account if audit else '',
                **event_account_context(event, audit, accounts),
                'recipients': recipients,
            })
        return Response({'count': count, 'results': results})

    @action(
        ['GET'], detail=True, url_path='secret',
        permission_classes=[RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    )
    def get_once_secret(self, request, *args, **kwargs):
        instance = self.get_object()
        response = Response(data={
            'id': instance.id, 'secret': instance.secret,
            'org_id': str(instance.org_id),
            'endpoint': request.build_absolute_uri('/').rstrip('/'),
        })
        response['Cache-Control'] = 'no-store'
        return response
    
    @action(
        ['POST'], detail=True, url_path='reset-secret',
        permission_classes=[RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    )
    def reset_secret(self, request, *args, **kwargs):
        instance = self.get_object()
        self.start_audit(AuditEvent.APPLICATION_SECRET_RESET, application=instance)
        secret = instance.refresh_secret()
        record(AuditEvent.APPLICATION_SECRET_RESET, application=instance)
        response = Response(data={'id': instance.id, 'secret': secret})
        response['Cache-Control'] = 'no-store'
        return response



class ApplicationWebhookViewSet(OrgBulkModelViewSet):
    model = ApplicationWebhook
    serializer_class = serializers.ApplicationWebhookSerializer
    rbac_perms = {
        'metadata': 'accounts.view_applicationwebhook',
        'test_webhook': 'accounts.change_applicationwebhook',
    }
    filterset_fields = ('is_active', 'applications')
    search_fields = ('name', 'comment')
    ordering_fields = ('name', 'date_created')

    @action(['GET'], detail=False)
    def metadata(self, request, *args, **kwargs):
        return Response({
            'event_options': [
                {'value': value, 'label': str(label)}
                for value, label in ApplicationEvent.choices
            ],
            'template_variables': webhook_template_variables(),
            'default_template': default_application_webhook_template(),
        })

    def render_body(self, request, instance):
        event = request.data.get('event') or (instance.events[0] if instance.events else None)
        if event not in ApplicationEvent.values:
            raise ValidationError({'event': _('Select a supported webhook event.')})
        application = instance.applications.order_by('name').first()
        if not application:
            raise ValidationError({'applications': _('Select at least one application.')})
        template = request.data.get('body_template', instance.body_template)
        try:
            return render_webhook_template(template, sample_webhook_context(application, event))
        except WebhookValidationError as exc:
            raise ValidationError({'body_template': str(exc)}) from exc

    @action(['POST'], detail=True, url_path='test')
    def test_webhook(self, request, *args, **kwargs):
        instance = self.get_object()
        data = {key: value for key, value in request.data.items() if key != 'event'}
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        url = values.get('url', instance.url)
        events = values.get('events', instance.events)
        event = request.data.get('event') or (events[0] if events else None)
        if not url:
            raise ValidationError({'url': _('URL is required to test the webhook.')})
        if event not in events:
            raise ValidationError({'event': _('Select one of the subscribed webhook events.')})
        body = self.render_body(request, instance)
        from accounts.credential_client.webhook_delivery import WebhookRequestError, send_webhook
        try:
            status_code = send_webhook(
                values.get('method', instance.method), url,
                values.get('headers', instance.headers), body,
            )
        except WebhookRequestError as exc:
            return Response({
                'success': False, 'status_code': getattr(exc, 'status_code', None),
                'reason': exc.reason,
            })
        success = 200 <= status_code < 300
        return Response({
            'success': success, 'status_code': status_code,
            'reason': '' if success else 'http_error',
        })


class PythonSDKDownloadAPI(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        from accounts.credential_client.artifacts import artifact_url
        return HttpResponseRedirect(artifact_url('jms-pam-python.zip'))


class PAMClientSourceDownloadAPI(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, language, *args, **kwargs):
        from accounts.clients.distribution import SOURCE_FILES
        from accounts.credential_client.artifacts import artifact_url
        from rest_framework.exceptions import NotFound
        if language not in SOURCE_FILES:
            raise NotFound()
        return HttpResponseRedirect(artifact_url(f'jms-pam-{language}-source.tar.gz'))
