import os

from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import translation
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.models import ServiceIntegration
from audits.models import ServiceAccessLog
from authentication.permissions import UserConfirmation, ConfirmType
from common.exceptions import JMSException
from common.permissions import IsValidUser
from common.utils import get_request_ip
from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission


class ServiceIntegrationViewSet(OrgBulkModelViewSet):
    model = ServiceIntegration
    search_fields = ('name', 'comment')
    serializer_classes = {
        'default': serializers.ServiceIntegrationSerializer,
        'get_account_secret': serializers.ServiceAccountSecretSerializer
    }
    rbac_perms = {
        'get_once_secret': 'accounts.change_serviceintegration',
        'get_account_secret': 'accounts.view_serviceintegration',
    }

    @action(
        ['GET'], detail=False, url_path='sdks',
        permission_classes=[IsValidUser]
    )
    def get_sdks_info(self, request, *args, **kwargs):
        readme = ''
        sdk_language = self.request.query_params.get('language', 'python')
        filename = f'readme.{translation.get_language()}.md'
        readme_path = os.path.join(
            settings.APPS_DIR, 'accounts', 'demos', sdk_language, filename
        )
        if os.path.exists(readme_path):
            with open(readme_path, 'r') as f:
                readme = f.read()
        return Response(data={'readme': readme })

    @action(
        ['GET'], detail=True, url_path='secret',
        permission_classes=[RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    )
    def get_once_secret(self, request, *args, **kwargs):
        instance = self.get_object()
        secret = instance.get_secret()
        return Response(data={'id': instance.id, 'secret': secret})

    @action(['GET'], detail=False, url_path='account-secret')
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
        ServiceAccessLog.objects.create(
            remote_addr=get_request_ip(request), service=service.name, service_id=service.id,
            account=f'{account.name}({account.username})', asset=f'{asset.name}({asset.address})',
        )
        return Response(data={'id': request.user.id, 'secret': account.secret})

