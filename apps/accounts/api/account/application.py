import os
import zipfile
from uuid import UUID
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse
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
        'get_account_secret': serializers.IntegrationAccountSecretSerializer,
    }
    rbac_perms = {
        'get_once_secret': 'accounts.change_integrationapplication',
        'reset_secret': 'accounts.change_integrationapplication',
        'get_account_secret': 'accounts.view_integrationapplication',
        'get_sdks_info': 'accounts.view_integrationapplication',
        'credential_events': 'accounts.view_integrationapplication',
        'access_materials': 'accounts.change_integrationapplication',
        'send_event_options': 'accounts.change_integrationapplication',
        'send_event': 'accounts.change_integrationapplication',
        'manual_events': 'accounts.view_integrationapplication',
    }

    def read_file(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as file:
                return file.read()
        return ''

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
        sdk_language = request.query_params.get('language', 'python')
        if sdk_language != 'python':
            raise ValidationError(_('Credential policies currently support the Python SDK only.'))
        sdk_path = os.path.join(settings.APPS_DIR, 'accounts', 'demos', sdk_language)
        readme_path = os.path.join(sdk_path, f'README.{get_language()}.md')
        demo_path = os.path.join(sdk_path, 'demo.py')

        readme_content = self.read_file(readme_path)
        if not readme_content:
            readme_content = self.read_file(os.path.join(sdk_path, 'README.en.md'))
        demo_content = self.read_file(demo_path)

        return Response(data={'readme': readme_content, 'code': demo_content})

    @action(['GET'], detail=True, url_path='credential-events')
    def credential_events(self, request, *args, **kwargs):
        application = self.get_object()
        try:
            limit = min(max(int(request.query_params.get('limit', 30)), 1), 100)
            offset = max(int(request.query_params.get('offset', 0)), 0)
        except (TypeError, ValueError):
            raise ValidationError(_('Invalid pagination parameters.'))
        application_id = str(application.id)
        events = CredentialRotationEvent.objects.filter(
            org_id=application.org_id,
            recipients__contains=[{'application': {'id': application_id}}],
        ).order_by('-published_at', '-id')
        count = events.count()
        page = list(events[offset:offset + limit])
        audits = {
            str(audit.id): audit for audit in ApplicationAudit.objects.filter(
                id__in=[event.source_event_id for event in page],
                org_id=application.org_id,
            )
        }
        results = []
        for event in page:
            audit = audits.get(str(event.source_event_id))
            recipients = [
                {
                    'instance_id': recipient['instance_id'],
                    'type': recipient['type'],
                    'configuration': recipient['configuration']['name'],
                    'publish_result': recipient['publish_result'],
                    'received_at': recipient['received_at'],
                }
                for recipient in event.recipients
                if recipient['application']['id'] == application_id
            ]
            results.append({
                'id': str(event.source_event_id),
                'event': event.event,
                'published_at': event.published_at,
                'revision': event.revision,
                'rotation_id': str(event.rotation_id) if event.rotation_id else None,
                'credential_id': str(audit.credential_id) if audit and audit.credential_id else None,
                'credential': audit.credential if audit else '',
                'account': audit.account if audit else '',
                'recipients': recipients,
            })
        return Response({'count': count, 'results': results})

    @action(
        ['GET'], detail=True, url_path='secret',
        permission_classes=[RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    )
    def get_once_secret(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(data={'id': instance.id, 'secret': instance.secret})
    
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

    @action(['GET'], detail=False, url_path='account-secret',
            permission_classes=[RBACPermission])
    def get_account_secret(self, request, *args, **kwargs):
        self.start_audit(AuditEvent.CREDENTIAL_FETCHED, application=request.user)
        serializer = self.get_serializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=400)

        service = request.user
        account = service.get_account(**serializer.data)
        if not account:
            msg = _('Account not found')
            raise JMSException(code='Not found', detail='%s' % msg)
        # 根据配置决定是否返回密码
        secret = None if settings.SECURITY_DISABLE_VIEW_SECRET else account.secret
        record(AuditEvent.CREDENTIAL_FETCHED, application=service, account=account,
               remote_addr=get_request_ip(request), result='success' if secret is not None else 'failed',
               summary='Legacy account-secret access.')
        if secret is not None:
            from accounts.credential_rotation.preparation import record_secret_access
            record_secret_access(account, service)
        response = Response(data={'id': request.user.id, 'secret': secret})
        response['X-API-Deprecated'] = 'true'
        response['Warning'] = '299 JumpServer "Use /api/v1/accounts/credential-client/credential/ instead."'
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
        package_dir = os.path.join(settings.APPS_DIR, 'accounts', 'demos', 'python')
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for root, dirs, files in os.walk(package_dir):
                dirs[:] = [name for name in dirs if name != '__pycache__']
                for filename in files:
                    if filename.endswith(('.pyc', '.pyo')):
                        continue
                    path = os.path.join(root, filename)
                    archive.write(path, os.path.relpath(path, package_dir))
        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="jms-pam-python.zip"'
        return response
