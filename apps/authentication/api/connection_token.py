import os
import urllib.parse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status


from common.drf.api import JMSModelViewSet
from common.http import is_true
from orgs.mixins.api import RootOrgViewMixin
from perms.models.base import Action
from terminal.models import EndpointRule
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
        'get_rdp_file': 'authentication.add_connectiontoken',
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
        # 非常重要的 api，在逻辑层再判断一下，双重保险
        perm_required = 'authentication.view_connectiontokensecret'
        if not request.user.has_perm(perm_required):
            raise PermissionDenied('Not allow to view secret')
        token_id = request.data.get('token') or ''
        token = get_object_or_404(ConnectionToken, pk=token_id)
        is_valid, error = token.check_valid()
        if not is_valid:
            return Response(data={'error': error}, status=status.HTTP_403_FORBIDDEN)
        token.load_extra_attrs()
        serializer = self.get_serializer(instance=token)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['POST', 'GET'], detail=False, url_path='rdp/file')
    def get_rdp_file(self, request, *args, **kwargs):
        data = request.query_params if request.method == 'GET' else request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        token: ConnectionToken = serializer.instance
        is_valid, error = token.check_valid()
        if not is_valid:
            return Response(data={'error': error}, status=status.HTTP_403_FORBIDDEN)
        token.load_extra_attrs()
        filename, content = self.get_rdp_file_info(token)
        response = HttpResponse(content, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'%s' % filename
        return response

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
        endpoint = self.get_smart_endpoint(
            protocol='rdp', asset=token.asset, application=token.application
        )
        rdp_options['full address:s'] = f'{endpoint.host}:{endpoint.rdp_port}'

        # 设置用户名
        rdp_options['username:s'] = '{}|{}'.format(token.user.username, str(token.id))
        if token.system_user.ad_domain:
            rdp_options['domain:s'] = token.system_user.ad_domain

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
            name = token.asset.hostname
        elif token.application and token.application.category_remote_app:
            app = '||jmservisor'
            name = token.application.name
            rdp_options['remoteapplicationmode:i'] = '1'
            rdp_options['alternate shell:s'] = app
            rdp_options['remoteapplicationprogram:s'] = app
            rdp_options['remoteapplicationname:s'] = name
        else:
            name = '*'

        filename = "{}-{}-jumpserver.rdp".format(token.user.username, name)
        filename = urllib.parse.quote(filename)

        content = ''
        for k, v in rdp_options.items():
            content += f'{k}:{v}\n'

        return filename, content

    def get_smart_endpoint(self, protocol, asset=None, application=None):
        if asset:
            target_ip = asset.get_target_ip()
        elif application:
            target_ip = application.get_target_ip()
        else:
            target_ip = ''
        endpoint = EndpointRule.match_endpoint(target_ip, protocol, self.request)
        return endpoint

    @staticmethod
    def parse_env_bool(env_key, env_default, true_value, false_value):
        return true_value if is_true(os.getenv(env_key, env_default)) else false_value

