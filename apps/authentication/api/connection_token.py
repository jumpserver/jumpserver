# -*- coding: utf-8 -*-
#
import urllib.parse
import json
from typing import Callable
import os
import base64
import ctypes

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext as _
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers

from applications.models import Application
from authentication.signals import post_auth_failed
from common.utils import get_logger, random_string
from common.mixins.api import SerializerMixin
from common.utils.common import get_file_by_arch
from orgs.mixins.api import RootOrgViewMixin
from common.http import is_true
from perms.models.base import Action
from perms.utils.application.permission import get_application_actions
from perms.utils.asset.permission import get_asset_actions
from common.const.http import PATCH
from terminal.models import EndpointRule
from ..serializers import (
    ConnectionTokenSerializer, ConnectionTokenSecretSerializer,
)

logger = get_logger(__name__)
__all__ = ['UserConnectionTokenViewSet', 'TokenCacheMixin']


class ClientProtocolMixin:
    """
    下载客户端支持的连接文件，里面包含了 token，和 其他连接信息

    - [x] RDP
    - [ ] KoKo

    本质上，这里还是暴露出 token 来，进行使用
    """
    request: Request
    get_serializer: Callable
    create_token: Callable
    get_serializer_context: Callable

    def get_smart_endpoint(self, protocol, asset=None, application=None):
        if asset:
            target_ip = asset.get_target_ip()
        elif application:
            target_ip = application.get_target_ip()
        else:
            target_ip = ''
        endpoint = EndpointRule.match_endpoint(target_ip, protocol, self.request)
        return endpoint

    def get_request_resource(self, serializer):
        asset = serializer.validated_data.get('asset')
        application = serializer.validated_data.get('application')
        system_user = serializer.validated_data['system_user']

        user = serializer.validated_data.get('user')
        if not user or not self.request.user.is_superuser:
            user = self.request.user
        return asset, application, system_user, user

    @staticmethod
    def parse_env_bool(env_key, env_default, true_value, false_value):
        return true_value if is_true(os.getenv(env_key, env_default)) else false_value

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
            'smart sizing:i': '1',
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
        token, secret = self.create_token(user, asset, application, system_user)

        # 设置磁盘挂载
        if drives_redirect:
            actions = 0
            if asset:
                actions = get_asset_actions(user, asset, system_user)
            elif application:
                actions = get_application_actions(user, application, system_user)

            if actions & Action.UPDOWNLOAD == Action.UPDOWNLOAD:
                options['drivestoredirect:s'] = '*'

        # 全屏
        options['screen mode id:i'] = '2' if full_screen else '1'

        # RDP Server 地址
        endpoint = self.get_smart_endpoint(
            protocol='rdp', asset=asset, application=application
        )
        options['full address:s'] = f'{endpoint.host}:{endpoint.rdp_port}'
        # 用户名
        options['username:s'] = '{}|{}'.format(user.username, token)
        if system_user.ad_domain:
            options['domain:s'] = system_user.ad_domain
        # 宽高
        if width and height:
            options['desktopwidth:i'] = width
            options['desktopheight:i'] = height
            options['winposstr:s:'] = f'0,1,0,0,{width},{height}'

        options['session bpp:i'] = os.getenv('JUMPSERVER_COLOR_DEPTH', '32')
        options['audiomode:i'] = self.parse_env_bool('JUMPSERVER_DISABLE_AUDIO', 'false', '2', '0')

        if asset:
            name = asset.hostname
        elif application:
            name = application.name
            application.get_rdp_remote_app_setting()

            app = f'||jmservisor'
            options['remoteapplicationmode:i'] = '1'
            options['alternate shell:s'] = app
            options['remoteapplicationprogram:s'] = app
            options['remoteapplicationname:s'] = name
            options['remoteapplicationcmdline:s'] = '- ' + self.get_encrypt_cmdline(application)
        else:
            name = '*'

        content = ''
        for k, v in options.items():
            content += f'{k}:{v}\n'
        return name, content

    def get_ssh_token(self, serializer):
        asset, application, system_user, user = self.get_request_resource(serializer)
        token, secret = self.create_token(user, asset, application, system_user)
        if asset:
            name = asset.hostname
        elif application:
            name = application.name
        else:
            name = '*'

        endpoint = self.get_smart_endpoint(
            protocol='ssh', asset=asset, application=application
        )
        content = {
            'ip': endpoint.host,
            'port': str(endpoint.ssh_port),
            'username': f'JMS-{token}',
            'password': secret
        }
        token = json.dumps(content)
        return name, token

    def get_encrypt_cmdline(self, app: Application):
        parameters = app.get_rdp_remote_app_setting()['parameters']
        parameters = parameters.encode('ascii')

        lib_path = get_file_by_arch('xpack/libs', 'librailencrypt.so')
        lib = ctypes.CDLL(lib_path)
        lib.encrypt.argtypes = [ctypes.c_char_p, ctypes.c_int]
        lib.encrypt.restype = ctypes.c_char_p

        rst = lib.encrypt(parameters, len(parameters))
        rst = rst.decode('ascii')
        return rst

    @action(methods=['POST', 'GET'], detail=False, url_path='rdp/file')
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
        username = user.username
        config, token = '', ''
        if protocol == 'rdp':
            name, config = self.get_rdp_file_content(serializer)
        elif protocol == 'ssh':
            name, token = self.get_ssh_token(serializer)
        else:
            raise ValueError('Protocol not support: {}'.format(protocol))

        filename = "{}-{}-jumpserver".format(username, name)
        data = {
            "filename": filename,
            "protocol": system_user.protocol,
            "username": username,
            "token": token,
            "config": config
        }
        return data

    @action(methods=['POST', 'GET'], detail=False, url_path='client-url')
    def get_client_protocol_url(self, request, *args, **kwargs):
        serializer = self.get_valid_serializer()
        try:
            protocol_data = self.get_client_protocol_data(serializer)
        except ValueError as e:
            return Response({'error': str(e)}, status=401)

        protocol_data = json.dumps(protocol_data).encode()
        protocol_data = base64.b64encode(protocol_data).decode()
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
        gateway = None
        remote_app = None
        asset = None

        if application.category_remote_app:
            remote_app = application.get_rdp_remote_app_setting()
            asset = application.get_remote_app_asset()
            domain = asset.domain
        else:
            domain = application.domain

        if domain and domain.has_gateway():
            gateway = domain.random_gateway()

        return {
            'asset': asset,
            'application': application,
            'gateway': gateway,
            'domain': domain,
            'remote_app': remote_app,
        }

    @staticmethod
    def _get_asset_secret_detail(asset):
        gateway = None
        if asset and asset.domain and asset.domain.has_gateway():
            gateway = asset.domain.random_gateway()

        return {
            'asset': asset,
            'application': None,
            'domain': asset.domain,
            'gateway': gateway,
            'remote_app': None,
        }

    @action(methods=['POST'], detail=False, url_path='secret-info/detail')
    def get_secret_detail(self, request, *args, **kwargs):
        perm_required = 'authentication.view_connectiontokensecret'

        # 非常重要的 api，再逻辑层再判断一下，双重保险
        if not request.user.has_perm(perm_required):
            raise PermissionDenied('Not allow to view secret')

        token = request.data.get('token', '')
        try:
            value, user, system_user, asset, app, expired_at, actions = self.valid_token(token)
        except serializers.ValidationError as e:
            post_auth_failed.send(
                sender=self.__class__, username='', request=self.request,
                reason=_('Invalid token')
            )
            raise e

        data = dict(
            id=token, secret=value.get('secret', ''),
            user=user, system_user=system_user,
            expired_at=expired_at, actions=actions
        )
        cmd_filter_kwargs = {
            'system_user_id': system_user.id,
            'user_id': user.id,
        }
        if asset:
            asset_detail = self._get_asset_secret_detail(asset)
            system_user.load_asset_more_auth(asset.id, user.username, user.id)
            data['type'] = 'asset'
            data.update(asset_detail)
            cmd_filter_kwargs['asset_id'] = asset.id
        else:
            app_detail = self._get_application_secret_detail(app)
            system_user.load_app_more_auth(app.id, user.username, user.id)
            data['type'] = 'application'
            data.update(app_detail)
            cmd_filter_kwargs['application_id'] = app.id

        from assets.models import CommandFilterRule
        cmd_filter_rules = CommandFilterRule.get_queryset(**cmd_filter_kwargs)
        data['cmd_filter_rules'] = cmd_filter_rules

        serializer = self.get_serializer(data)
        return Response(data=serializer.data, status=200)


class TokenCacheMixin:
    """ endpoint smart view 用到此类来解析token中的资产、应用 """
    CACHE_KEY_PREFIX = 'CONNECTION_TOKEN_{}'

    def get_token_cache_key(self, token):
        return self.CACHE_KEY_PREFIX.format(token)

    def get_token_ttl(self, token):
        key = self.get_token_cache_key(token)
        return cache.ttl(key)

    def set_token_to_cache(self, token, value, ttl=5*60):
        key = self.get_token_cache_key(token)
        cache.set(key, value, timeout=ttl)

    def get_token_from_cache(self, token):
        key = self.get_token_cache_key(token)
        value = cache.get(key, None)
        return value

    def renewal_token(self, token, ttl=5*60):
        value = self.get_token_from_cache(token)
        if value:
            pre_ttl = self.get_token_ttl(token)
            self.set_token_to_cache(token, value, ttl)
            post_ttl = self.get_token_ttl(token)
            ok = True
            msg = f'{pre_ttl}s is renewed to {post_ttl}s.'
        else:
            ok = False
            msg = 'Token is not found.'
        data = {
            'ok': ok,
            'msg': msg
        }
        return data


class UserConnectionTokenViewSet(
    RootOrgViewMixin, SerializerMixin, ClientProtocolMixin,
    SecretDetailMixin, TokenCacheMixin, GenericViewSet
):
    serializer_classes = {
        'default': ConnectionTokenSerializer,
        'get_secret_detail': ConnectionTokenSecretSerializer,
    }
    rbac_perms = {
        'GET': 'authentication.view_connectiontoken',
        'create': 'authentication.add_connectiontoken',
        'renewal': 'authentication.add_superconnectiontoken',
        'get_secret_detail': 'authentication.view_connectiontokensecret',
        'get_rdp_file': 'authentication.add_connectiontoken',
        'get_client_protocol_url': 'authentication.add_connectiontoken',
    }

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

    @action(methods=[PATCH], detail=False)
    def renewal(self, request, *args, **kwargs):
        """ 续期 Token """
        perm_required = 'authentication.add_superconnectiontoken'
        if not request.user.has_perm(perm_required):
            raise PermissionDenied('No permissions for authentication.add_superconnectiontoken')
        token = request.data.get('token', '')
        data = self.renewal_token(token)
        status_code = 200 if data.get('ok') else 404
        return Response(data=data, status=status_code)

    def create_token(self, user, asset, application, system_user, ttl=5*60):
        # 再次强调一下权限
        perm_required = 'authentication.add_superconnectiontoken'
        if user != self.request.user and not self.request.user.has_perm(perm_required):
            raise PermissionDenied('Only can create user token')
        self.check_resource_permission(user, asset, application, system_user)
        token = random_string(36)
        secret = random_string(16)
        value = {
            'id': token,
            'secret': secret,
            'user': str(user.id),
            'username': user.username,
            'system_user': str(system_user.id),
            'system_user_name': system_user.name,
            'created_by': str(self.request.user),
            'date_created': str(timezone.now())
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

        self.set_token_to_cache(token, value, ttl)
        return token, secret

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        asset, application, system_user, user = self.get_request_resource(serializer)
        token, secret = self.create_token(user, asset, application, system_user)
        tp = 'app' if application else 'asset'
        data = {
            "id": token, 'secret': secret,
            'type': tp, 'protocol': system_user.protocol,
            'expire_time': self.get_token_ttl(token),
        }
        return Response(data, status=201)

    def valid_token(self, token):
        from users.models import User
        from assets.models import SystemUser, Asset
        from applications.models import Application
        from perms.utils.asset.permission import validate_permission as asset_validate_permission
        from perms.utils.application.permission import validate_permission as app_validate_permission

        value = self.get_token_from_cache(token)
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
            has_perm, actions, expired_at = asset_validate_permission(user, asset, system_user)
        else:
            app = get_object_or_404(Application, id=value.get('application'))
            has_perm, actions, expired_at = app_validate_permission(user, app, system_user)

        if not has_perm:
            raise serializers.ValidationError('Permission expired or invalid')
        return value, user, system_user, asset, app, expired_at, actions

    def get(self, request):
        token = request.query_params.get('token')
        value = self.get_token_from_cache(token)
        if not value:
            return Response('', status=404)
        return Response(value)
