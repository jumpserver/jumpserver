# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.serializers import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from common.utils import get_logger, random_string
from common.drf.api import SerializerMixin2
from common.permissions import IsSuperUserOrAppUser, IsValidUser, IsSuperUser

from orgs.mixins.api import RootOrgViewMixin

from ..serializers import ConnectionTokenSerializer, ConnectionTokenSecretSerializer

logger = get_logger(__name__)
__all__ = ['UserConnectionTokenViewSet']


class UserConnectionTokenViewSet(RootOrgViewMixin, SerializerMixin2, GenericViewSet):
    permission_classes = (IsSuperUserOrAppUser,)
    serializer_classes = {
        'default': ConnectionTokenSerializer,
        'get_secret_detail': ConnectionTokenSecretSerializer
    }
    CACHE_KEY_PREFIX = 'CONNECTION_TOKEN_{}'

    @staticmethod
    def check_resource_permission(user, asset, application, system_user):
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
        return True

    def create_token(self, user, asset, application, system_user):
        self.check_resource_permission(user, asset, application, system_user)
        token = random_string(36)
        value = {
            'user': str(user.id),
            'username': user.username,
            'system_user': str(system_user.id),
            'system_user_name': system_user.name
        }

        if asset:
            value.update({
                'type': 'asset',
                'asset': str(asset.id),
                'hostname': asset.hostname,
            })
        elif application:
            value.update({
                'type': 'application',
                'application': application.id,
                'application_name': str(application)
            })

        key = self.CACHE_KEY_PREFIX.format(token)
        cache.set(key, value, timeout=20)
        return token

    def create(self, request, *args, **kwargs):
        if not settings.CONNECTION_TOKEN_ENABLED:
            data = {'error': 'Connection token disabled'}
            return Response(data, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data.get('user', None)
        if not request.user.is_superuser and user:
            raise PermissionDenied('Only super user can create user token')
        if not request.user.is_superuser:
            user = self.request.user

        asset = serializer.validated_data.get('asset')
        application = serializer.validated_data.get('application')
        system_user = serializer.validated_data['system_user']

        token = self.create_token(user, asset, application, system_user)
        return Response({"token": token}, status=201)

    @staticmethod
    def _get_application_secret_detail(value):
        from applications.models import Application
        from perms.models import Action
        application = get_object_or_404(Application, id=value.get('application'))
        gateway = None

        if not application.category_remote_app:
            actions = Action.NONE
            remote_app = {}
            asset = None
            domain = application.domain
        else:
            remote_app = application.get_rdp_remote_app_setting()
            actions = Action.CONNECT
            asset = application.get_remote_app_asset()
            domain = asset.domain

        if domain and domain.has_gateway():
            gateway = domain.random_gateway()

        return {
            'asset': asset,
            'application': application,
            'gateway': gateway,
            'remote_app': remote_app,
            'actions': actions
        }

    @staticmethod
    def _get_asset_secret_detail(value, user, system_user):
        from assets.models import Asset
        from perms.utils.asset import get_asset_system_users_id_with_actions_by_user
        asset = get_object_or_404(Asset, id=value.get('asset'))
        systemuserid_actions_mapper = get_asset_system_users_id_with_actions_by_user(user, asset)
        actions = systemuserid_actions_mapper.get(system_user.id, [])
        gateway = None
        if asset and asset.domain and asset.domain.has_gateway():
            gateway = asset.domain.random_gateway()
        return {
            'asset': asset,
            'application': None,
            'gateway': gateway,
            'remote_app': None,
            'actions': actions,
        }

    @action(methods=['POST'], detail=False, permission_classes=[IsSuperUserOrAppUser], url_path='secret-info/detail')
    def get_secret_detail(self, request, *args, **kwargs):
        from users.models import User
        from assets.models import SystemUser

        token = request.data.get('token', '')
        key = self.CACHE_KEY_PREFIX.format(token)
        value = cache.get(key, None)
        if not value:
            return Response(status=404)
        user = get_object_or_404(User, id=value.get('user'))
        system_user = get_object_or_404(SystemUser, id=value.get('system_user'))
        data = dict(user=user, system_user=system_user)

        if value.get('type') == 'asset':
            asset_detail = self._get_asset_secret_detail(value, user=user, system_user=system_user)
            data['type'] = 'asset'
            data.update(asset_detail)
        else:
            app_detail = self._get_application_secret_detail(value)
            data['type'] = 'application'
            data.update(app_detail)

        serializer = self.get_serializer(data)
        return Response(data=serializer.data, status=200)

    def get_permissions(self):
        if self.action == "create":
            if self.request.data.get('user', None):
                self.permission_classes = (IsSuperUser,)
            else:
                self.permission_classes = (IsValidUser,)
        return super().get_permissions()

    def get(self, request):
        token = request.query_params.get('token')
        key = self.CACHE_KEY_PREFIX.format(token)
        value = cache.get(key, None)

        if not value:
            return Response('', status=404)
        return Response(value)
