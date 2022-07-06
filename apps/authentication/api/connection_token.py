from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status


from common.drf.api import JMSModelViewSet
from orgs.mixins.api import RootOrgViewMixin
from ..serializers import ConnectionTokenSerializer, ConnectionTokenSecretSerializer
from ..models import ConnectionToken


__all__ = ['ConnectionTokenViewSet']


class ConnectionTokenViewSet(RootOrgViewMixin, JMSModelViewSet):
    serializer_classes = {
        'default': ConnectionTokenSerializer,
        'get_secret_detail': ConnectionTokenSecretSerializer,
    }
    rbac_perms = {
        'retrieve': 'authentication.view_connectiontoken',
        'create': 'authentication.add_connectiontoken',
        'get_secret_detail': 'authentication.view_connectiontokensecret',
    }
    queryset = ConnectionToken.objects.all()

    @staticmethod
    def get_request_resources(serializer):
        user = serializer.validated_data.get('user')  # or self.request.user
        asset = serializer.validated_data.get('asset')
        application = serializer.validated_data.get('application')
        system_user = serializer.validated_data.get('system_user')
        return user, asset, application, system_user

    def perform_create(self, serializer):
        user, asset, application, system_user = self.get_request_resources(serializer)
        self.check_user_has_resource_permission(user, asset, application, system_user)
        return super(ConnectionTokenViewSet, self).perform_create(serializer)

    @staticmethod
    def check_user_has_resource_permission(user, asset, application, system_user):
        from perms.utils.asset import has_asset_system_permission
        from perms.utils.application import has_application_system_permission

        if asset and not has_asset_system_permission(user, asset, system_user):
            error = f'User not has this asset and system user permission: ' \
                    f'user={user.id} system_user={system_user.id} asset={asset.id}'
            raise PermissionDenied(error)

        if application and not has_application_system_permission(user, application, system_user):
            error = f'User not has this application and system user permission: ' \
                    f'user={user.id} system_user={system_user.id} application={application.id}'
            raise PermissionDenied(error)

    @action(methods=['POST'], detail=False, url_path='secret-info/detail')
    def get_secret_detail(self, request, *args, **kwargs):
        # 非常重要的 api，再逻辑层再判断一下，双重保险
        perm_required = 'authentication.view_connectiontokensecret'
        if not request.user.has_perm(perm_required):
            raise PermissionDenied('Not allow to view secret')
        token_id = request.data.get('token') or ''
        token = get_object_or_404(ConnectionToken, pk=token_id)
        is_valid, error = token.check_valid()
        if not is_valid:
            return Response(data={'error': error}, status=status.HTTP_403_FORBIDDEN)
        token.load_secret_detail_attrs()
        serializer = self.get_serializer(instance=token)
        return Response(serializer.data, status=status.HTTP_200_OK)
