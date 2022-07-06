from rest_framework.exceptions import PermissionDenied

from common.drf.api import JMSModelViewSet
from orgs.mixins.api import RootOrgViewMixin
from ..serializers import ConnectionTokenSerializer


__all__ = ['ConnectionTokenViewSet']


class ConnectionTokenViewSet(RootOrgViewMixin, JMSModelViewSet):
    serializer_classes = {
        'default': ConnectionTokenSerializer,
    }

    rbac_perms = {
        'create': 'authentication.add_connectiontoken',
    }

    def get_request_resources(self, serializer):
        user = serializer.validated_data.get('user') or self.request.user
        asset = serializer.validated_data.get('asset')
        application = serializer.validated_data.get('application')
        system_user = serializer.validated_data.get('system_user')
        return user, asset, application, system_user

    def create(self, request, *args, **kwargs):
        return super(ConnectionTokenViewSet, self).create(request, *args, **kwargs)

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

