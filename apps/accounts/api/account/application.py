import os
import shlex
import zipfile
from io import BytesIO

from django.conf import settings
from django.core import signing
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _, get_language
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import serializers
from accounts.filters import IntegrationApplicationFilterSet
from accounts.models import IntegrationApplication
from audits.models import IntegrationApplicationLog
from authentication.permissions import UserConfirmation, ConfirmType
from common.exceptions import JMSException
from common.permissions import IsValidUser
from common.utils import get_request_ip, random_string
from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission


class IntegrationApplicationViewSet(OrgBulkModelViewSet):
    model = IntegrationApplication
    filterset_class = IntegrationApplicationFilterSet
    search_fields = ('name', 'comment')
    serializer_classes = {
        'default': serializers.IntegrationApplicationSerializer,
        'get_account_secret': serializers.IntegrationAccountSecretSerializer
    }
    rbac_perms = {
        'get_once_secret': 'accounts.change_integrationapplication',
        'get_account_secret': 'accounts.view_integrationapplication',
        'get_sdks_info': 'accounts.view_integrationapplication',
        'refresh_secret': 'accounts.change_integrationapplication',
        'agent_registration': 'accounts.change_integrationapplication',
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
        code_suffix_mapper = {
            'python': 'py',
            'java': 'java',
            'go': 'go',
            'node': 'js',
            'curl': 'sh',
        }
        sdk_language = request.query_params.get('language', 'python')
        sdk_path = os.path.join(settings.APPS_DIR, 'accounts', 'demos', sdk_language)
        readme_path = os.path.join(sdk_path, f'README.{get_language()}.md')
        demo_path = os.path.join(sdk_path, f'demo.{code_suffix_mapper[sdk_language]}')

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
        ['GET'], detail=True, url_path='refresh-secret',
        permission_classes=[RBACPermission]
    )
    def refresh_secret(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.refresh_secret()
        return Response(data={'id': instance.id, 'msg': 'Successfully refreshed secret'})

    @action(['POST'], detail=True, url_path='agent-registration')
    def agent_registration(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.credential_access_mode != IntegrationApplication.AccessMode.agent:
            raise JMSException(
                code='invalid_access_mode',
                detail=_('The integration application does not use Agent access mode.'),
            )
        token = signing.dumps({
            'application_id': str(instance.id),
            'org_id': instance.org_id,
            'nonce': random_string(24),
        }, salt='credential-agent-register')
        endpoint = request.build_absolute_uri('/').rstrip('/')
        credential_keys = request.data.get('credential_keys') or []
        app_user = request.data.get('app_user') or ''
        instance_id = request.data.get('instance_id') or ''
        if not isinstance(credential_keys, list) or not credential_keys:
            raise ValidationError({'credential_keys': _('At least one credential key is required.')})
        if not all(isinstance(key, str) and key for key in credential_keys):
            raise ValidationError({'credential_keys': _('Invalid credential key.')})
        if not isinstance(app_user, str) or not app_user:
            raise ValidationError({'app_user': _('This field is required.')})
        if not isinstance(instance_id, str) or not instance_id:
            raise ValidationError({'instance_id': _('This field is required.')})
        credentials = ' '.join(
            f'--credential {shlex.quote(key)}' for key in credential_keys
        )
        endpoint_arg = shlex.quote(endpoint)
        token_arg = shlex.quote(token)
        return Response({
            'token': token,
            'expires_in': 600,
            'download_url': f'{endpoint}/api/v1/accounts/python-sdk/',
            'install_command': (
                'sudo python3 -m venv /opt/jumpserver-pam/venv && '
                f'sudo /opt/jumpserver-pam/venv/bin/pip install {endpoint_arg}/api/v1/accounts/python-sdk/ && '
                f'sudo /opt/jumpserver-pam/venv/bin/jms-pam-agent install --endpoint {endpoint_arg} '
                f'--token {token_arg} --instance-id {shlex.quote(instance_id)} '
                f'{credentials} --app-user {shlex.quote(app_user)}'
            ),
        })

    @action(['GET'], detail=False, url_path='account-secret',
            permission_classes=[RBACPermission])
    def get_account_secret(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=400)

        service = request.user
        account = service.get_account(**serializer.data)
        if not account:
            msg = _('Account not found')
            raise JMSException(code='Not found', detail='%s' % msg)
        asset = account.asset
        IntegrationApplicationLog.objects.create(
            remote_addr=get_request_ip(request), service=service.name, service_id=service.id,
            account=f'{account.name}({account.username})', asset=f'{asset.name}({asset.address})',
        )
        
        # 根据配置决定是否返回密码
        secret = None if settings.SECURITY_DISABLE_VIEW_SECRET else account.secret
        return Response(data={'id': request.user.id, 'secret': secret})


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
