import os
import abc
import json
import time
import base64
import urllib.parse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request

from common.drf.api import JMSModelViewSet
from common.http import is_true
from orgs.mixins.api import RootOrgViewMixin
from perms.models import Action
from terminal.models import EndpointRule
from ..serializers import (
    ConnectionTokenSerializer, ConnectionTokenSecretSerializer,
    SuperConnectionTokenSerializer, ConnectionTokenDisplaySerializer,
)
from ..models import ConnectionToken

__all__ = ['ConnectionTokenViewSet', 'SuperConnectionTokenViewSet']

# ExtraActionApiMixin


class RDPFileClientProtocolURLMixin:
    request: Request
    get_serializer: callable

    def get_rdp_file_info(self, token: ConnectionToken):
        rdp_options = {
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
            # 'drivestoredirect:s': '*',
            # 'domain:s': ''
            # 'alternate shell:s:': '||MySQLWorkbench',
            # 'remoteapplicationname:s': 'Firefox',
            # 'remoteapplicationcmdline:s': '',
        }

        # 设置磁盘挂载
        drives_redirect = is_true(self.request.query_params.get('drives_redirect'))
        if drives_redirect:
            actions = Action.choices_to_value(token.actions)
            if actions & Action.UPDOWNLOAD == Action.UPDOWNLOAD:
                rdp_options['drivestoredirect:s'] = '*'

        # 设置全屏
        full_screen = is_true(self.request.query_params.get('full_screen'))
        rdp_options['screen mode id:i'] = '2' if full_screen else '1'

        # 设置 RDP Server 地址
        endpoint = self.get_smart_endpoint(protocol='rdp', asset=token.asset)
        rdp_options['full address:s'] = f'{endpoint.host}:{endpoint.rdp_port}'

        # 设置用户名
        rdp_options['username:s'] = '{}|{}'.format(token.user.username, str(token.id))
        # rdp_options['domain:s'] = token.account_ad_domain

        # 设置宽高
        height = self.request.query_params.get('height')
        width = self.request.query_params.get('width')
        if width and height:
            rdp_options['desktopwidth:i'] = width
            rdp_options['desktopheight:i'] = height
            rdp_options['winposstr:s:'] = f'0,1,0,0,{width},{height}'

        # 设置其他选项
        rdp_options['session bpp:i'] = os.getenv('JUMPSERVER_COLOR_DEPTH', '32')
        rdp_options['audiomode:i'] = self.parse_env_bool('JUMPSERVER_DISABLE_AUDIO', 'false', '2', '0')

        if token.asset:
            name = token.asset.name
            # remote-app
            # app = '||jmservisor'
            # rdp_options['remoteapplicationmode:i'] = '1'
            # rdp_options['alternate shell:s'] = app
            # rdp_options['remoteapplicationprogram:s'] = app
            # rdp_options['remoteapplicationname:s'] = name
        else:
            name = '*'
        prefix_name = f'{token.user.username}-{name}'
        filename = self.get_connect_filename(prefix_name)

        content = ''
        for k, v in rdp_options.items():
            content += f'{k}:{v}\n'

        return filename, content

    @staticmethod
    def get_connect_filename(prefix_name):
        prefix_name = prefix_name.replace('/', '_')
        prefix_name = prefix_name.replace('\\', '_')
        prefix_name = prefix_name.replace('.', '_')
        filename = f'{prefix_name}-jumpserver'
        filename = urllib.parse.quote(filename)
        return filename

    @staticmethod
    def parse_env_bool(env_key, env_default, true_value, false_value):
        return true_value if is_true(os.getenv(env_key, env_default)) else false_value

    def get_client_protocol_data(self, token: ConnectionToken):
        protocol = token.protocol
        username = token.user.username
        rdp_config = ssh_token = ''
        if protocol == 'rdp':
            filename, rdp_config = self.get_rdp_file_info(token)
        elif protocol == 'ssh':
            filename, ssh_token = self.get_ssh_token(token)
        else:
            raise ValueError('Protocol not support: {}'.format(protocol))

        return {
            "filename": filename,
            "protocol": protocol,
            "username": username,
            "token": ssh_token,
            "config": rdp_config
        }

    def get_ssh_token(self, token: ConnectionToken):
        if token.asset:
            name = token.asset.name
        else:
            name = '*'
        prefix_name = f'{token.user.username}-{name}'
        filename = self.get_connect_filename(prefix_name)

        endpoint = self.get_smart_endpoint(protocol='ssh', asset=token.asset)
        data = {
            'ip': endpoint.host,
            'port': str(endpoint.ssh_port),
            'username': 'JMS-{}'.format(str(token.id)),
            'password': token.secret
        }
        token = json.dumps(data)
        return filename, token

    def get_smart_endpoint(self, protocol, asset=None):
        target_ip = asset.get_target_ip() if asset else ''
        endpoint = EndpointRule.match_endpoint(target_ip, protocol, self.request)
        return endpoint


class ExtraActionApiMixin(RDPFileClientProtocolURLMixin):
    request: Request
    get_object: callable
    get_serializer: callable
    perform_create: callable
    check_token_permission: callable
    create_connection_token: callable

    @action(methods=['POST'], detail=False, url_path='secret-info/detail')
    def get_secret_detail(self, request, *args, **kwargs):
        """ 非常重要的 api, 在逻辑层再判断一下 rbac 权限, 双重保险 """
        rbac_perm = 'authentication.view_connectiontokensecret'
        if not request.user.has_perm(rbac_perm):
            raise PermissionDenied('Not allow to view secret')
        token_id = request.data.get('token') or ''
        token = get_object_or_404(ConnectionToken, pk=token_id)
        self.check_token_permission(token)
        serializer = self.get_serializer(instance=token)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['POST', 'GET'], detail=False, url_path='rdp/file')
    def get_rdp_file(self, request, *args, **kwargs):
        token = self.create_connection_token()
        self.check_token_permission(token)
        filename, content = self.get_rdp_file_info(token)
        filename = '{}.rdp'.format(filename)
        response = HttpResponse(content, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'%s' % filename
        return response

    @action(methods=['POST', 'GET'], detail=False, url_path='client-url')
    def get_client_protocol_url(self, request, *args, **kwargs):
        token = self.create_connection_token()
        self.check_token_permission(token)
        try:
            protocol_data = self.get_client_protocol_data(token)
        except ValueError as e:
            return Response(data={'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        protocol_data = json.dumps(protocol_data).encode()
        protocol_data = base64.b64encode(protocol_data).decode()
        data = {
            'url': 'jms://{}'.format(protocol_data)
        }
        return Response(data=data)

    @action(methods=['PATCH'], detail=True)
    def expire(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.expire()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def check_token_permission(token: ConnectionToken):
        is_valid, error = token.check_permission()
        if not is_valid:
            raise PermissionDenied(error)

    def create_connection_token(self):
        data = self.request.query_params if self.request.method == 'GET' else self.request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        token: ConnectionToken = serializer.instance
        return token


class ConnectionTokenViewSet(ExtraActionApiMixin, RootOrgViewMixin, JMSModelViewSet):
    filterset_fields = (
        'user_display', 'asset_display'
    )
    search_fields = filterset_fields
    serializer_classes = {
        'default': ConnectionTokenSerializer,
        'list': ConnectionTokenDisplaySerializer,
        'retrieve': ConnectionTokenDisplaySerializer,
        'get_secret_detail': ConnectionTokenSecretSerializer,
    }
    rbac_perms = {
        'retrieve': 'authentication.view_connectiontoken',
        'create': 'authentication.add_connectiontoken',
        'expire': 'authentication.add_connectiontoken',
        'get_secret_detail': 'authentication.view_connectiontokensecret',
        'get_rdp_file': 'authentication.add_connectiontoken',
        'get_client_protocol_url': 'authentication.add_connectiontoken',
    }

    def get_queryset(self):
        return ConnectionToken.objects.filter(user=self.request.user)

    def get_user(self, serializer):
        return self.request.user

    def perform_create(self, serializer):
        user = self.get_user(serializer)
        asset = serializer.validated_data.get('asset')
        account_username = serializer.validated_data.get('account_username')
        self.validate_asset_permission(user, asset, account_username)
        return super(ConnectionTokenViewSet, self).perform_create(serializer)

    @staticmethod
    def validate_asset_permission(user, asset, account_username):
        from perms.utils.account import PermAccountUtil
        actions, expire_at = PermAccountUtil().validate_permission(user, asset, account_username)
        if not actions:
            error = ''
            raise PermissionDenied(error)
        if expire_at < time.time():
            error = ''
            raise PermissionDenied(error)


# SuperConnectionToken


class SuperConnectionTokenViewSet(ConnectionTokenViewSet):
    serializer_classes = {
        'default': SuperConnectionTokenSerializer,
    }
    rbac_perms = {
        'create': 'authentication.add_superconnectiontoken',
        'renewal': 'authentication.add_superconnectiontoken'
    }

    def get_queryset(self):
        return ConnectionToken.objects.all()

    def get_user(self, serializer):
        return serializer.validated_data.get('user')

    @action(methods=['PATCH'], detail=False)
    def renewal(self, request, *args, **kwargs):
        from common.utils.timezone import as_current_tz

        token_id = request.data.get('token') or ''
        token = get_object_or_404(ConnectionToken, pk=token_id)
        date_expired = as_current_tz(token.date_expired)
        if token.is_expired:
            raise PermissionDenied('Token is expired at: {}'.format(date_expired))
        token.renewal()
        data = {
            'ok': True,
            'msg': f'Token is renewed, date expired: {date_expired}'
        }
        return Response(data=data, status=status.HTTP_200_OK)
