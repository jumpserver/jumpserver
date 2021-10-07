# -*- coding: utf-8 -*-
#
import urllib.parse
import json
import base64
from typing import Callable

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils.translation import ugettext as _
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers

from authentication.signals import post_auth_failed, post_auth_success
from common.utils import get_logger, random_string
from common.drf.api import SerializerMixin
from common.permissions import IsSuperUserOrAppUser, IsValidUser, IsSuperUser
from orgs.mixins.api import RootOrgViewMixin
from common.http import is_true
from perms.utils.asset.permission import get_asset_system_user_ids_with_actions_by_user
from perms.models.asset_permission import Action
from authentication.errors import NotHaveUpDownLoadPerm

from ..serializers import (
    ConnectionTokenSerializer, ConnectionTokenSecretSerializer,
)

logger = get_logger(__name__)
__all__ = ['UserConnectionTokenViewSet']


class ClientProtocolMixin:
    request: Request
    get_serializer: Callable
    create_token: Callable

    def get_request_resource(self, serializer):
        asset = serializer.validated_data.get('asset')
        application = serializer.validated_data.get('application')
        system_user = serializer.validated_data['system_user']

        user = serializer.validated_data.get('user')
        if not user or not self.request.user.is_superuser:
            user = self.request.user
        return asset, application, system_user, user

    def get_rdp_file_content(self, serializer):
        options = {
            'full address:s': '',
            'username:s': '',
            # 'screen mode id:i': '1',
            # 'desktopwidth:i': '1280',
            # 'desktopheight:i': '800',
            'use multimon:i': '0',
            'session bpp:i': '32',
            'audiomode:i': '0',
            'disable wallpaper:i': '0',
            'disable full window drag:i': '0',
            'disable menu anims:i': '0',
            'disable themes:i': '0',
            'alternate shell:s': '',
            'shell working directory:s': '',
            'authentication level:i': '2',
            'connect to console:i': '0',
            'disable cursor setting:i': '0',
            'allow font smoothing:i': '1',
            'allow desktop composition:i': '1',
            'redirectprinters:i': '0',
            'prompt for credentials on client:i': '0',
            'autoreconnection enabled:i': '1',
            'bookmarktype:i': '3',
            'use redirection server name:i': '0',
            'smart sizing:i': '0',
            #'drivestoredirect:s': '*',
            # 'domain:s': ''
            # 'alternate shell:s:': '||MySQLWorkbench',
            # 'remoteapplicationname:s': 'Firefox',
            # 'remoteapplicationcmdline:s': '',
        }

        asset, application, system_user, user = self.get_request_resource(serializer)
        height = self.request.query_params.get('height')
        width = self.request.query_params.get('width')
        full_screen = is_true(self.request.query_params.get('full_screen'))
        drives_redirect = is_true(self.request.query_params.get('drives_redirect'))
        token = self.create_token(user, asset, application, system_user)

        if drives_redirect and asset:
            systemuser_actions_mapper = get_asset_system_user_ids_with_actions_by_user(user, asset)
            actions = systemuser_actions_mapper.get(system_user.id, [])
            if actions & Action.UPDOWNLOAD:
                options['drivestoredirect:s'] = '*'
            else:
                raise NotHaveUpDownLoadPerm

        options['screen mode id:i'] = '2' if full_screen else '1'
        address = settings.TERMINAL_RDP_ADDR
        if not address or address == 'localhost:3389':
            address = self.request.get_host().split(':')[0] + ':3389'
        options['full address:s'] = address
        options['username:s'] = '{}|{}'.format(user.username, token)
        if system_user.ad_domain:
            options['domain:s'] = system_user.ad_domain
        if width and height:
            options['desktopwidth:i'] = width
            options['desktopheight:i'] = height
        else:
            options['smart sizing:i'] = '1'
        content = ''
        for k, v in options.items():
            content += f'{k}:{v}\n'
        if asset:
            name = asset.hostname
        elif application:
            name = application.name
        else:
            name = '*'
        return name, content

    @action(methods=['POST', 'GET'], detail=False, url_path='rdp/file', permission_classes=[IsValidUser])
    def get_rdp_file(self, request, *args, **kwargs):
        if self.request.method == 'GET':
            data = self.request.query_params
        else:
            data = self.request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        name, data = self.get_rdp_file_content(serializer)
        response = HttpResponse(data, content_type='application/octet-stream')
        filename = "{}-{}-jumpserver.rdp".format(self.request.user.username, name)
        filename = urllib.parse.quote(filename)
        response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'%s' % filename
        return response

    def get_valid_serializer(self):
        if self.request.method == 'GET':
            data = self.request.query_params
        else:
            data = self.request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer

    def get_client_protocol_data(self, serializer):
        asset, application, system_user, user = self.get_request_resource(serializer)
        protocol = system_user.protocol
        if protocol == 'rdp':
            name, config = self.get_rdp_file_content(serializer)
        elif protocol == 'vnc':
            raise HttpResponse(status=404, data={"error": "VNC not support"})
        else:
            config = 'ssh://system_user@asset@user@jumpserver-ssh'
        data = {
            "protocol": system_user.protocol,
            "username": user.username,
            "config": config
        }
        return data

    @action(methods=['POST', 'GET'], detail=False, url_path='client-url', permission_classes=[IsValidUser])
    def get_client_protocol_url(self, request, *args, **kwargs):
        serializer = self.get_valid_serializer()
        protocol_data = self.get_client_protocol_data(serializer)
        protocol_data = base64.b64encode(json.dumps(protocol_data).encode()).decode()
        data = {
            'url': 'jms://{}'.format(protocol_data),
        }
        return Response(data=data)


class SecretDetailMixin:
    valid_token: Callable
    request: Request
    get_serializer: Callable

    @staticmethod
    def _get_application_secret_detail(application):
        from perms.models import Action
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
    def _get_asset_secret_detail(asset, user, system_user):
        from perms.utils.asset import get_asset_system_user_ids_with_actions_by_user
        systemuserid_actions_mapper = get_asset_system_user_ids_with_actions_by_user(user, asset)
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
        token = request.data.get('token', '')
        try:
            value, user, system_user, asset, app, expired_at = self.valid_token(token)
        except serializers.ValidationError as e:
            post_auth_failed.send(
                sender=self.__class__, username='', request=self.request,
                reason=_('Invalid token')
            )
            raise e

        data = dict(user=user, system_user=system_user, expired_at=expired_at)
        if asset:
            asset_detail = self._get_asset_secret_detail(asset, user=user, system_user=system_user)
            system_user.load_asset_more_auth(asset.id, user.username, user.id)
            data['type'] = 'asset'
            data.update(asset_detail)
        else:
            app_detail = self._get_application_secret_detail(app)
            system_user.load_app_more_auth(app.id, user.id)
            data['type'] = 'application'
            data.update(app_detail)

        self.request.session['auth_backend'] = settings.AUTH_BACKEND_AUTH_TOKEN
        post_auth_success.send(sender=self.__class__, user=user, request=self.request, login_type='T')

        serializer = self.get_serializer(data)
        return Response(data=serializer.data, status=200)


class UserConnectionTokenViewSet(
    RootOrgViewMixin, SerializerMixin, ClientProtocolMixin,
    SecretDetailMixin, GenericViewSet
):
    permission_classes = (IsSuperUserOrAppUser,)
    serializer_classes = {
        'default': ConnectionTokenSerializer,
        'get_secret_detail': ConnectionTokenSecretSerializer,
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

    def create_token(self, user, asset, application, system_user, ttl=5 * 60):
        if not self.request.user.is_superuser and user != self.request.user:
            raise PermissionDenied('Only super user can create user token')
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
        cache.set(key, value, timeout=ttl)
        return token

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        asset, application, system_user, user = self.get_request_resource(serializer)
        token = self.create_token(user, asset, application, system_user)
        return Response({"token": token}, status=201)

    def valid_token(self, token):
        from users.models import User
        from assets.models import SystemUser, Asset
        from applications.models import Application
        from perms.utils.asset.permission import validate_permission as asset_validate_permission
        from perms.utils.application.permission import validate_permission as app_validate_permission

        key = self.CACHE_KEY_PREFIX.format(token)
        value = cache.get(key, None)
        if not value:
            raise serializers.ValidationError('Token not found')

        user = get_object_or_404(User, id=value.get('user'))
        if not user.is_valid:
            raise serializers.ValidationError("User not valid, disabled or expired")

        system_user = get_object_or_404(SystemUser, id=value.get('system_user'))

        asset = None
        app = None
        if value.get('type') == 'asset':
            asset = get_object_or_404(Asset, id=value.get('asset'))
            if not asset.is_active:
                raise serializers.ValidationError("Asset disabled")

            has_perm, expired_at = asset_validate_permission(user, asset, system_user, 'connect')
        else:
            app = get_object_or_404(Application, id=value.get('application'))
            has_perm, expired_at = app_validate_permission(user, app, system_user)

        if not has_perm:
            raise serializers.ValidationError('Permission expired or invalid')
        return value, user, system_user, asset, app, expired_at

    def get_permissions(self):
        if self.action in ["create", "get_rdp_file"]:
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
