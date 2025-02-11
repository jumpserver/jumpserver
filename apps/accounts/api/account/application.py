import os
from django.utils.translation import gettext_lazy as _, get_language
from django.conf import settings
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.models import IntegrationApplication
from audits.models import IntegrationApplicationLog
from authentication.permissions import UserConfirmation, ConfirmType
from common.exceptions import JMSException
from common.permissions import IsValidUser
from common.utils import get_request_ip
from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission


class IntegrationApplicationViewSet(OrgBulkModelViewSet):
    model = IntegrationApplication
    search_fields = ('name', 'comment')
    serializer_classes = {
        'default': serializers.IntegrationApplicationSerializer,
        'get_account_secret': serializers.IntegrationAccountSecretSerializer
    }
    rbac_perms = {
        'get_once_secret': 'accounts.change_integrationapplication',
        'get_account_secret': 'accounts.view_integrationapplication'
    }

    @action(
        ['GET'], detail=False, url_path='sdks',
        permission_classes=[IsValidUser]
    )
    def get_sdks_info(self, request, *args, **kwargs):
        code_suffix_mapper = {
            'python': 'py',
            'java': 'java',
            'go': 'go',
            'javascript': 'js',
            'php': 'php',
        }
        sdk_language = request.query_params.get('language','python')
        sdk_path = os.path.join(settings.APPS_DIR, 'accounts', 'demos', sdk_language)
        readme_path = os.path.join(sdk_path, f'readme.{get_language()}.md')
        demo_path = os.path.join(sdk_path, f'demo.{code_suffix_mapper[sdk_language]}')

        def read_file(path):
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            return ''

        return Response(data={'readme': read_file(readme_path), 'code': read_file(demo_path)})

    @action(
        ['GET'], detail=True, url_path='secret',
        permission_classes=[RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    )
    def get_once_secret(self, request, *args, **kwargs):
        instance = self.get_object()
        secret = instance.get_secret()
        return Response(data={'id': instance.id, 'secret': secret})

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
        return Response(data={'id': request.user.id, 'secret': account.secret})
