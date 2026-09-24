import os
import zipfile
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _, get_language
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import serializers
from accounts.const import ApplicationEvent, AuditEvent
from accounts.filters import IntegrationApplicationFilterSet
from accounts.models import ApplicationWebhook, IntegrationApplication
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
    }

    def read_file(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as file:
                return file.read()
        return ''

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
        record(AuditEvent.CREDENTIAL_FETCHED, application=service, remote_addr=get_request_ip(request),
               summary='Legacy account-secret access.')
        
        # 根据配置决定是否返回密码
        secret = None if settings.SECURITY_DISABLE_VIEW_SECRET else account.secret
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
