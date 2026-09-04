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
from accounts.filters import IntegrationApplicationFilterSet
from accounts.models import IntegrationApplication
from audits.models import IntegrationApplicationLog
from authentication.permissions import UserConfirmation, ConfirmType
from common.exceptions import JMSException
from common.utils import get_request_ip
from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission


class IntegrationApplicationViewSet(OrgBulkModelViewSet):
    model = IntegrationApplication
    filterset_class = IntegrationApplicationFilterSet
    search_fields = ('name', 'comment')
    serializer_classes = {
        'default': serializers.IntegrationApplicationSerializer,
        'get_account_secret': serializers.IntegrationAccountSecretSerializer,
    }
    rbac_perms = {
        'get_once_secret': 'accounts.change_integrationapplication',
        'get_account_secret': 'accounts.view_integrationapplication',
        'get_sdks_info': 'accounts.view_integrationapplication',
        'refresh_secret': 'accounts.change_integrationapplication',
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
            raise ValidationError(_('Application credentials currently support the Python SDK only.'))
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
        ['GET'], detail=True, url_path='refresh-secret',
        permission_classes=[RBACPermission]
    )
    def refresh_secret(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.refresh_secret()
        return Response(data={'id': instance.id, 'msg': 'Successfully refreshed secret'})

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
        response = Response(data={'id': request.user.id, 'secret': secret})
        response['X-API-Deprecated'] = 'true'
        response['Warning'] = '299 JumpServer "Use /api/v1/accounts/credential-client/credential/ instead."'
        response['Cache-Control'] = 'no-store'
        return response


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
