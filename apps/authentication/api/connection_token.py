import base64
import json
import os
import urllib.parse
from collections.abc import Mapping
from struct import pack

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.settings import api_settings
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.personal_credentials import (
    get_personal_credential_failure_reason,
    record_personal_credential_audit,
)
from assets.const import Protocol
from assets.models import Asset
from common.api import JMSModelViewSet
from common.exceptions import JMSException
from common.utils import (
    get_logger, get_request_ip_or_data, is_uuid,
)
from common.utils.django import get_request_os
from common.utils.http import is_true
from orgs.mixins.api import RootOrgViewMixin
from orgs.models import Organization
from orgs.utils import get_org_from_request, tmp_to_org, tmp_to_root_org
from perms.models import ActionChoices
from terminal.connect_methods import NativeClient, ConnectMethodUtil
from terminal.models import EndpointRule, Endpoint
from users.const import RDPKeyboardHook
from ..models import ConnectionToken, AdminConnectionToken, date_expired_default
from ..services.connection_token import (
    ConnectionTokenService, get_connection_token_secret, record_connection_token_credential_audit,
)
from ..utils import (
    build_absolute_uri,
    should_use_oracle_sysdba,
)
from ..serializers import (
    ConnectionTokenSerializer, ConnectionTokenSecretSerializer,
    SuperConnectionTokenSerializer, ConnectTokenAppletOptionSerializer,
    ConnectionTokenReusableSerializer, ConnectTokenVirtualAppOptionSerializer,
    AdminConnectionTokenSerializer,
)

__all__ = ['ConnectionTokenViewSet', 'SuperConnectionTokenViewSet', 'AdminConnectionTokenViewSet']
logger = get_logger(__name__)


class RDPFileClientProtocolURLMixin:
    request: Request
    get_serializer: callable

    RDP_SIGN_SECURE_SETTINGS = [
        ('full address:s:', 'Full Address'),
        ('alternate full address:s:', 'Alternate Full Address'),
        ('pcb:s:', 'PCB'),
        ('use redirection server name:i:', 'Use Redirection Server Name'),
        ('server port:i:', 'Server Port'),
        ('negotiate security layer:i:', 'Negotiate Security Layer'),
        ('enablecredsspsupport:i:', 'EnableCredSspSupport'),
        ('disableconnectionsharing:i:', 'DisableConnectionSharing'),
        ('autoreconnection enabled:i:', 'AutoReconnection Enabled'),
        ('gatewayhostname:s:', 'GatewayHostname'),
        ('gatewayusagemethod:i:', 'GatewayUsageMethod'),
        ('gatewayprofileusagemethod:i:', 'GatewayProfileUsageMethod'),
        ('gatewaycredentialssource:i:', 'GatewayCredentialsSource'),
        ('support url:s:', 'Support URL'),
        ('promptcredentialonce:i:', 'PromptCredentialOnce'),
        ('require pre-authentication:i:', 'Require pre-authentication'),
        ('pre-authentication server address:s:', 'Pre-authentication server address'),
        ('alternate shell:s:', 'Alternate Shell'),
        ('shell working directory:s:', 'Shell Working Directory'),
        ('remoteapplicationprogram:s:', 'RemoteApplicationProgram'),
        ('remoteapplicationexpandworkingdir:s:', 'RemoteApplicationExpandWorkingdir'),
        ('remoteapplicationmode:i:', 'RemoteApplicationMode'),
        ('remoteapplicationguid:s:', 'RemoteApplicationGuid'),
        ('remoteapplicationname:s:', 'RemoteApplicationName'),
        ('remoteapplicationicon:s:', 'RemoteApplicationIcon'),
        ('remoteapplicationfile:s:', 'RemoteApplicationFile'),
        ('remoteapplicationfileextensions:s:', 'RemoteApplicationFileExtensions'),
        ('remoteapplicationcmdline:s:', 'RemoteApplicationCmdLine'),
        ('remoteapplicationexpandcmdline:s:', 'RemoteApplicationExpandCmdLine'),
        ('prompt for credentials:i:', 'Prompt For Credentials'),
        ('authentication level:i:', 'Authentication Level'),
        ('audiomode:i:', 'AudioMode'),
        ('redirectdrives:i:', 'RedirectDrives'),
        ('redirectprinters:i:', 'RedirectPrinters'),
        ('redirectcomports:i:', 'RedirectCOMPorts'),
        ('redirectsmartcards:i:', 'RedirectSmartCards'),
        ('redirectposdevices:i:', 'RedirectPOSDevices'),
        ('redirectclipboard:i:', 'RedirectClipboard'),
        ('devicestoredirect:s:', 'DevicesToRedirect'),
        ('drivestoredirect:s:', 'DrivesToRedirect'),
        ('loadbalanceinfo:s:', 'LoadBalanceInfo'),
        ('redirectdirectx:i:', 'RedirectDirectX'),
        ('rdgiskdcproxy:i:', 'RDGIsKDCProxy'),
        ('kdcproxyname:s:', 'KDCProxyName'),
        ('eventloguploadaddress:s:', 'EventLogUploadAddress'),
        ('redirectwebauthn:i:', 'RedirectWebAuthn'),
    ]

    @classmethod
    def _collect_rdp_sign_lines(cls, settings_lines):
        signnames = []
        signlines = []
        for prefix, sign_name in cls.RDP_SIGN_SECURE_SETTINGS:
            for line in settings_lines:
                if line.startswith(prefix):
                    signnames.append(sign_name)
                    signlines.append(line)
        return signnames, signlines

    @classmethod
    def _try_sign_rdp_content(cls, content):
        if not settings.RDP_SIGN_ENABLED:
            return content
        cert_dir = os.path.join(settings.PROJECT_DIR, 'data', 'certs')
        if not os.path.exists(cert_dir):
            logger.error(f'rdp sign cert dir [{cert_dir}] not exists')
            return content
        
        certfile = os.path.join(cert_dir, settings.RDP_SIGN_CERT)
        if not os.path.exists(certfile):
            logger.error(f'rdp sign cert file [{certfile}] not exists')
            return content
        
        keyfile = os.path.join(cert_dir, settings.RDP_SIGN_CERT_KEY)
        if not os.path.exists(keyfile):
            logger.warning(f'rdp sign cert file [{keyfile}] not exists')
            keyfile = None
            return content

        settings_lines = []
        full_address = None
        alternate_full_address = None
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('signature:s:') or line.startswith('signscope:s:'):
                continue
            if line.startswith('full address:s:'):
                full_address = line[15:]
            elif line.startswith('alternate full address:s:'):
                alternate_full_address = line[25:]
            settings_lines.append(line)

        # Keep alternate full address aligned with full address to prevent tampering.
        if full_address and not alternate_full_address:
            settings_lines.append(f'alternate full address:s:{full_address}')

        signnames, signlines = cls._collect_rdp_sign_lines(settings_lines)
        if not signnames or not signlines:
            return content

        msgtext = '\r\n'.join(signlines) + '\r\n' + 'signscope:s:' + ','.join(signnames) + '\r\n' + '\x00'
        msgblob = msgtext.encode('UTF-16LE')

        try:
            with open(certfile, 'rb') as f:
                cert_pem = f.read()
            cert = x509.load_pem_x509_certificate(cert_pem)
            if keyfile:
                with open(keyfile, 'rb') as f:
                    key_pem = f.read()
            else:
                key_pem = cert_pem
            private_key = serialization.load_pem_private_key(key_pem, password=None)
            pkcs7_der = (
                pkcs7.PKCS7SignatureBuilder()
                .set_data(msgblob)
                .add_signer(cert, private_key, hashes.SHA256())
                .sign(
                    serialization.Encoding.DER,
                    [
                        pkcs7.PKCS7Options.Binary,
                        pkcs7.PKCS7Options.DetachedSignature,
                        pkcs7.PKCS7Options.NoAttributes,
                    ],
                )
            )
        except OSError as e:
            logger.warning('RDP file sign failed to read cert/key: %s', e)
            return content
        except ValueError as e:
            logger.warning('RDP file sign failed (invalid cert/key PEM): %s', e)
            return content
        except Exception as e:
            logger.warning('RDP file sign failed: %s', e)
            return content

        msgsig = pack('<I', 0x00010001)
        msgsig += pack('<I', 0x00000001)
        msgsig += pack('<I', len(pkcs7_der))
        msgsig += pkcs7_der
        sigval = base64.b64encode(msgsig).decode('ascii')

        signed_lines = settings_lines + [f'signscope:s:{",".join(signnames)}', f'signature:s:{sigval}']
        return '\n'.join(signed_lines) + '\n'

    def get_rdp_file_info(self, token: ConnectionToken):
        rdp_options = {
            'full address:s': '',
            'username:s': '',
            'use multimon:i': '0',
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
            'bitmapcachepersistenable:i': '0',
            'bitmapcachesize:i': '1500',
        }

        # copy from
        # https://learn.microsoft.com/zh-cn/windows-server/administration/performance-tuning/role/remote-desktop/session-hosts
        rdp_low_speed_broadband_option = {
            "connection type:i": 2,
            "disable wallpaper:i": 1,
            "disable full window drag:i": 1,
            "disable menu anims:i": 1,
            "allow font smoothing:i": 0,
            "allow desktop composition:i": 0,
            "disable themes:i": 0
        }

        rdp_high_speed_broadband_option = {
            "connection type:i": 4,
            "disable wallpaper:i": 0,
            "disable full window drag:i": 1,
            "disable menu anims:i": 0,
            "allow font smoothing:i": 0,
            "allow desktop composition:i": 1,
            "disable themes:i": 0
        }

        RDP_CONNECTION_SPEED_OPTION_MAP = {
            "auto": {},
            "low_speed_broadband": rdp_low_speed_broadband_option,
            "high_speed_broadband": rdp_high_speed_broadband_option,
        }

        client_options = token.user.preference.get_value(
            'rdp_client_option', category='luna',
            default=settings.LUNA_DEFAULT_RDP_CLIENT_OPTION
        )
        if isinstance(client_options, str):
            try:
                client_options = json.loads(client_options)
            except json.JSONDecodeError:
                client_options = settings.LUNA_DEFAULT_RDP_CLIENT_OPTION
        if not isinstance(client_options, (list, set, tuple)):
            client_options = settings.LUNA_DEFAULT_RDP_CLIENT_OPTION
        client_options = set(client_options)

        # 设置多屏显示
        multi_mon_value = self.request.query_params.get('multi_mon')
        multi_mon = 'multi_screen' in client_options if multi_mon_value is None else is_true(multi_mon_value)
        if multi_mon:
            rdp_options['use multimon:i'] = '1'

        # 设置打印机重定向
        printers_redirect_value = self.request.query_params.get('printers_redirect')
        if printers_redirect_value is None:
            printers_redirect_value = token.connect_options.get('printers_redirect')
        if printers_redirect_value is None:
            printers_redirect_value = token.user.preference.get_value(
                'printers_redirect', category='luna', default=False
            )
        # Boolean preferences are stored as "True"/"False" in a TextField.
        if isinstance(printers_redirect_value, str):
            printers_redirect_value = printers_redirect_value.lower()
        if is_true(printers_redirect_value):
            rdp_options['redirectprinters:i'] = '1'

        # Windows key combinations: this preference applies to desktop sessions.
        if token.connect_method == NativeClient.mstsc:
            keyboard_hook_value = self.request.query_params.get('rdp_keyboard_hook')
            keyboard_hook = keyboard_hook_value
            if keyboard_hook is None:
                keyboard_hook = token.user.preference.get_value(
                    'rdp_keyboard_hook', category='luna', default=RDPKeyboardHook.FULL_SCREEN
                )
            field = serializers.ChoiceField(choices=RDPKeyboardHook.choices)
            try:
                keyboard_hook = field.run_validation(keyboard_hook)
            except ValidationError as exc:
                if keyboard_hook_value is not None:
                    raise ValidationError({'rdp_keyboard_hook': exc.detail})
                # A stale or invalid stored preference must not prevent connecting.
                keyboard_hook = RDPKeyboardHook.FULL_SCREEN
            rdp_options['keyboardhook:i'] = keyboard_hook

        # 设置磁盘挂载
        drives_redirect_value = self.request.query_params.get('drives_redirect')
        drives_redirect = (
            'drives_redirect' in client_options
            if drives_redirect_value is None else is_true(drives_redirect_value)
        )
        if drives_redirect:
            if ActionChoices.contains(token.actions, ActionChoices.transfer()):
                rdp_options['drivestoredirect:s'] = '*'

        # 设置全屏
        full_screen_value = self.request.query_params.get('full_screen')
        full_screen = 'full_screen' in client_options if full_screen_value is None else is_true(full_screen_value)
        rdp_options['screen mode id:i'] = '2' if full_screen else '1'

        # 设置 RDP Server 地址
        endpoint = self.get_smart_endpoint(protocol='rdp', asset=token.asset)
        rdp_options['full address:s'] = f'{endpoint.host}:{endpoint.rdp_port}'

        # 设置用户名
        rdp_options['username:s'] = '{}|{}'.format(token.user.username, str(token.id))
        # rdp_options['domain:s'] = token.account_ad_domain

        # 设置宽高

        resolution_value = token.connect_options.get('resolution')
        if not resolution_value:
            resolution_value = token.user.preference.get_value(
                'rdp_resolution', category='luna',
                default=settings.LUNA_DEFAULT_RDP_RESOLUTION
            )
        if resolution_value != 'auto':
            width, height = resolution_value.split('x')
            if width and height:
                rdp_options['desktopwidth:i'] = width
                rdp_options['desktopheight:i'] = height
                rdp_options['winposstr:s'] = f'0,1,0,0,{width},{height}'
                rdp_options['dynamic resolution:i'] = '0'

        color_quality = self.request.query_params.get('rdp_color_quality')
        if not color_quality:
            color_quality = token.user.preference.get_value(
                'rdp_color_quality', category='luna',
                default=os.getenv('JUMPSERVER_COLOR_DEPTH', settings.LUNA_DEFAULT_RDP_COLOR_QUALITY)
            )

        # 设置其他选项
        rdp_options['session bpp:i'] = color_quality
        rdp_options['audiomode:i'] = self.parse_env_bool('JUMPSERVER_DISABLE_AUDIO', 'false', '2', '0')

        # 设置远程麦克风。请求参数用于兼容直接下载 RDP 文件的场景，
        # 连接令牌中的临时配置优先于用户偏好。
        remote_microphone_value = self.request.query_params.get('remote_microphone')
        if remote_microphone_value is None:
            remote_microphone_value = token.connect_options.get('remote_microphone')
        if remote_microphone_value is None:
            remote_microphone = 'remote_microphone' in client_options
        else:
            remote_microphone = is_true(remote_microphone_value)
        if remote_microphone:
            rdp_options['audiocapturemode:i'] = '1'

        smart_size = self.request.query_params.get('rdp_smart_size')
        if smart_size is None:
            smart_size = token.user.preference.get_value(
                'rdp_smart_size', category='luna',
                default=settings.LUNA_DEFAULT_RDP_SMART_SIZE
            )
        rdp_options['smart sizing:i'] = smart_size

        # 设置远程应用, 不是 Mstsc
        if token.connect_method != NativeClient.mstsc:
            remote_app_options = token.get_remote_app_option()
            rdp_options.update(remote_app_options)

        rdp = token.asset.platform.protocols.filter(name='rdp').first()
        if rdp and rdp.setting.get('console'):
            rdp_options['administrative session:i'] = '1'
        rdp_connection_speed = token.connect_options.get('rdp_connection_speed', 'auto')
        rdp_options.update(RDP_CONNECTION_SPEED_OPTION_MAP.get(rdp_connection_speed, {}))

        # 文件名
        name = token.asset.name
        prefix_name = f'{token.user.username}-{name}'
        filename = self.get_connect_filename(prefix_name)

        content = ''
        for k, v in rdp_options.items():
            content += f'{k}:{v}\n'

        content = self._try_sign_rdp_content(content)
        return filename, content

    @staticmethod
    def escape_name(name):
        name = name.replace('/', '_')
        name = name.replace('\\', '_')
        name = name.replace('.', '_')
        name = urllib.parse.quote(name)
        return name

    def get_connect_filename(self, prefix_name):
        filename = prefix_name
        filename = self.escape_name(filename)
        return filename

    @staticmethod
    def get_token_account_display(token):
        if token.personal_credential_id:
            return token.input_username or token.account
        try:
            account = token.account_object
        except Exception:
            account = None
        if account:
            return (
                account.full_username
                or account.username
                or account.name
                or token.account
            )
        return token.input_username or token.account
    @staticmethod
    def parse_env_bool(env_key, env_default, true_value, false_value):
        return true_value if is_true(os.getenv(env_key, env_default)) else false_value

    def get_client_protocol_data(self, token: ConnectionToken):
        _os = get_request_os(self.request)

        connect_method_name = token.connect_method
        connect_method_dict = ConnectMethodUtil.get_connect_method(
            token.connect_method, token.protocol, _os
        )
        asset = token.asset
        if connect_method_dict is None:
            raise ValueError('Connect method not support: {}'.format(connect_method_name))

        account = self.get_token_account_display(token)  #修改account
        datetime = timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H:%M:%S')
        name = account + '@' + asset.name + '[' + datetime + ']'
        data = {
            'version': 2,
            'id': str(token.id),  # 兼容老的，未来几个版本删掉
            'value': token.value,  # 兼容老的，未来几个版本删掉
            'name': self.escape_name(name),
            'protocol': token.protocol,
            'site_url': build_absolute_uri(self.request, '/').rstrip('/'),
            'org_id': str(token.org_id),
            'token': {
                'id': str(token.id),
                'value': token.value,
            },
            'file': {},
            'command': ''
        }

        if token.protocol == Protocol.oracle:
            data['connect_options'] = {
                'use_sysdba': should_use_oracle_sysdba(
                    token.connect_options, token.protocol, token.asset
                )
            }

        if connect_method_name == NativeClient.mstsc or connect_method_dict['type'] == 'applet':
            filename, content = self.get_rdp_file_info(token)
            data.update({
                'protocol': 'rdp',
                'file': {
                    'name': filename,
                    'content': content,
                }
            })
        else:
            if connect_method_dict['type'] == 'virtual_app':
                endpoint_protocol = 'vnc'
                token_protocol = 'vnc'
                data.update({
                    'protocol': 'vnc',
                })
            else:
                endpoint_protocol = connect_method_dict['endpoint_protocol']
                token_protocol = token.protocol

            endpoint = self.get_smart_endpoint(
                protocol=endpoint_protocol,
                asset=asset
            )
            data.update({
                'asset': {
                    'id': str(asset.id),
                    'category': asset.category,
                    'type': asset.type,
                    'name': asset.name,
                    'address': asset.address,
                    'info': {
                        **asset.spec_info,
                    }
                },
                'endpoint': {
                    'host': endpoint.host,
                    'port': endpoint.get_port(token.asset, token_protocol),
                }
            })
        return data

    def get_smart_endpoint(self, protocol, asset=None):
        endpoint = Endpoint.match_by_instance_label(asset, protocol, self.request)
        if not endpoint:
            target_ip = asset.get_target_ip() if asset else ''
            endpoint = EndpointRule.match_endpoint(
                target_instance=asset, target_ip=target_ip,
                protocol=protocol, request=self.request
            )
        return endpoint


class ExtraActionApiMixin(RDPFileClientProtocolURLMixin):
    request: Request
    get_object: callable
    get_serializer: callable
    perform_create: callable
    validate_exchange_token: callable
    need_face_verify: bool
    create_face_verify: callable

    @action(methods=['POST', 'GET'], detail=True, url_path='rdp-file')
    def get_rdp_file(self, request, *args, **kwargs):
        token = self.get_object()
        token.is_valid()
        filename, content = self.get_rdp_file_info(token)
        response = HttpResponse(content, content_type='application/octet-stream')

        if is_true(request.query_params.get('reusable')):
            token.set_reusable(True)
            filename = '{}-{}'.format(filename, token.date_expired.strftime('%Y%m%d_%H%M%S'))

        filename += '.rdp'
        response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'%s' % filename
        return response

    @action(methods=['POST', 'GET'], detail=True, url_path='client-url')
    def get_client_protocol_url(self, *args, **kwargs):
        token = self.get_object()
        token.is_valid()
        try:
            protocol_data = self.get_client_protocol_data(token)
        except ValueError as e:
            return Response(data={'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        protocol_data = json.dumps(protocol_data).encode()
        protocol_data = base64.b64encode(protocol_data).decode()
        data = {
            'url': 'jms2://{}'.format(protocol_data)
        }
        return Response(data=data)

    @action(methods=['PATCH'], detail=True)
    def expire(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.expire()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['PATCH'], detail=True, url_path='reuse')
    def reuse(self, request, *args, **kwargs):
        instance = self.get_object()
        if not settings.CONNECTION_TOKEN_REUSABLE:
            error = _('Reusable connection token is not allowed, global setting not enabled')
            raise serializers.ValidationError(error)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        is_reusable = serializer.validated_data.get('is_reusable', False)
        instance.set_reusable(is_reusable)
        return Response(data=serializer.data)

    @action(methods=['POST'], detail=False)
    @transaction.atomic
    def exchange(self, request, *args, **kwargs):
        pk = request.data.get('id', None) or request.data.get('pk', None)
        # 只能兑换自己使用的 Token
        instance = get_object_or_404(ConnectionToken, pk=pk, user=request.user)
        instance.id = None
        instance.from_ticket = None
        try:
            self.validate_exchange_token(instance)
        except APIException as error:
            record_connection_token_credential_audit(
                instance, result='failed', error=error, request=request,
            )
            raise
        instance.date_expired = date_expired_default()
        instance.save()
        serializer = self.get_serializer(instance)
        response = Response(serializer.data, status=status.HTTP_201_CREATED)
        if self.need_face_verify and not is_true(request.query_params.get('acl_stepwise')):
            self.create_face_verify(response)
        return response


class ConnectionTokenViewSet(ConnectionTokenService, ExtraActionApiMixin, RootOrgViewMixin, JMSModelViewSet):
    queryset = ConnectionToken.objects.none()
    filterset_fields = (
        'user_display', 'asset_display'
    )
    search_fields = filterset_fields
    serializer_classes = {
        'default': ConnectionTokenSerializer,
        'reuse': ConnectionTokenReusableSerializer,
    }
    http_method_names = ['get', 'post', 'patch', 'head', 'options', 'trace']
    rbac_perms = {
        'list': 'authentication.view_connectiontoken',
        'retrieve': 'authentication.view_connectiontoken',
        'create': 'authentication.add_connectiontoken',
        'exchange': 'authentication.add_connectiontoken',
        'acl_controls': 'authentication.add_connectiontoken',
        'acl_batch': 'authentication.add_connectiontoken',
        'reuse': 'authentication.reuse_connectiontoken',
        'expire': 'authentication.expire_connectiontoken',
        'get_rdp_file': 'authentication.add_connectiontoken',
        'get_client_protocol_url': 'authentication.add_connectiontoken',
    }

    def get_queryset(self):
        queryset = ConnectionToken.objects.filter(user=self.request.user)
        if self.action != 'acl_controls':
            queryset = queryset.filter(date_expired__gt=timezone.now())
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        return self.create_token(serializer)

    def record_personal_credential_failure(self, reason):
        context = self.personal_credential_audit_context
        if not context:
            return
        try:
            record_personal_credential_audit(
                result='failed',
                failure_reason=reason,
                user=self.request.user,
                remote_addr=get_request_ip_or_data(self.request),
                **context,
            )
        except Exception:
            logger.exception('Record personal credential failure audit failed')


    @action(methods=['GET', 'POST'], detail=True, url_path='acl')
    @transaction.atomic
    def acl_controls(self, request, *args, **kwargs):
        from authentication.services.connection_acl import advance_acl
        instance = self.get_object()
        if request.method == 'GET':
            return Response(self.get_serializer(instance).data)
        token = advance_acl(instance, request)
        response = Response(self.get_serializer(token).data)
        if request.method == 'POST' and is_true(request.data.get('retry_face')) and not token.acl_context.get('cancelled') and token.acl_context.get('requirements', {}).get('face') == 'pending':
            self.create_face_verify(response)
        return response

    @action(methods=['POST'], detail=False, url_path='acl/batch')
    @transaction.atomic
    def acl_batch(self, request, *args, **kwargs):
        from authentication.serializers.connection_token import ConnectionACLBatchInputSerializer
        from authentication.services.connection_acl_batch import advance_acl_batch
        serializer = ConnectionACLBatchInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Scope is server-derived. A token ID never grants access to another user or token type.
        model = AdminConnectionToken if isinstance(self, AdminConnectionTokenViewSet) else ConnectionToken
        with tmp_to_root_org():
            tokens = list(model.objects.select_for_update().filter(
                pk__in=data['token_ids'], user=request.user, type=model._type,
            ).order_by('pk'))
        if len(tokens) != len(data['token_ids']):
            raise PermissionDenied(_('Connection is no longer available'), code='connection_unavailable')
        for token in tokens:
            with tmp_to_org(token.org_id):
                self.check_permissions(request)
        tokens = advance_acl_batch(tokens, request, data)
        if data['step'] == 'face' and data.get('retry_face'):
            pending = [token for token in tokens if token.acl_context['requirements'].get('face') == 'pending']
            if pending:
                response = Response(self.get_serializer(pending[0]).data)
                with tmp_to_org(pending[0].org_id):
                    self.create_face_verify(response, tokens=pending)
                with tmp_to_root_org():
                    tokens = [model.objects.get(pk=token.pk) for token in tokens]
        return Response(self.get_serializer(tokens, many=True).data)

    def create_face_verify(self, response, *, tokens=None):
        response.data.update(super().create_face_verify(response.data.get('id'), tokens=tokens))

    @staticmethod
    def serialize_validation_error(detail):
        if isinstance(detail, dict):
            data = {}
            for field, messages in detail.items():
                if isinstance(messages, dict):
                    data[field] = ConnectionTokenViewSet.serialize_validation_error(messages)
                elif isinstance(messages, (list, tuple)):
                    data[field] = [str(message) for message in messages]
                else:
                    data[field] = [str(messages)]
            return data
        if isinstance(detail, (list, tuple)):
            return {api_settings.NON_FIELD_ERRORS_KEY: [str(item) for item in detail]}
        return {api_settings.NON_FIELD_ERRORS_KEY: [str(detail)]}

    def create(self, request, *args, **kwargs):
        self.personal_credential_audit_context = None
        self.personal_credential_saved = None
        raw_data = request.data if isinstance(request.data, Mapping) else {}
        raw_save = raw_data.get('save_personal_credential', False)
        save_credential = raw_save in (True, 1, '1', 'true', 'True')
        credential_id = raw_data.get('personal_credential_id')
        if credential_id or save_credential:
            raw_asset_id = raw_data.get('asset')
            if isinstance(raw_asset_id, Mapping):
                raw_asset_id = raw_asset_id.get('id') or raw_asset_id.get('pk')
            raw_asset = None
            if (
                    raw_asset_id
                    and not isinstance(raw_asset_id, (list, tuple))
                    and is_uuid(raw_asset_id)
            ):
                raw_asset = Asset.objects.filter(id=raw_asset_id).first()
            request_org = get_org_from_request(request)
            requested_audit_org_id = (
                raw_asset.org_id if raw_asset else request_org.id
            )
            can_audit_requested_org = (
                request.user.is_superuser
                or request.user.orgs.filter(
                    id=requested_audit_org_id
                ).exists()
            )
            if not can_audit_requested_org:
                raw_asset = None
                requested_audit_org_id = Organization.DEFAULT_ID
            self.personal_credential_audit_context = {
                'operation': (
                    'update' if credential_id and save_credential
                    else 'create' if save_credential
                    else 'use'
                ),
                'asset': raw_asset,
                'credential_id': credential_id,
                'username': raw_data.get('input_username', ''),
                'secret_type': raw_data.get('input_secret_type', ''),
                'org_id': requested_audit_org_id,
            }
        failure_reason = ''
        try:
            # Face context creation is part of the connection/save operation.
            # If it fails, roll back both the token and any inline credential.
            with transaction.atomic():
                response = super().create(request, *args, **kwargs)
                if self.need_face_verify and not is_true(request.query_params.get('acl_stepwise')):
                    self.create_face_verify(response)
        except JMSException as e:
            failure_reason = str(e.detail.code)
            data = {'code': e.detail.code, 'detail': e.detail}
            response = Response(data, status=e.status_code)
        except ValidationError as e:
            failure_reason = get_personal_credential_failure_reason(e)
            data = self.serialize_validation_error(e.detail)
            response = Response(data, status=e.status_code)
        except APIException as error:
            self.record_personal_credential_failure(
                get_personal_credential_failure_reason(error)
            )
            raise
        except Exception as error:
            self.record_personal_credential_failure(
                error.__class__.__name__
            )
            raise
        if failure_reason:
            self.record_personal_credential_failure(failure_reason)
        elif self.personal_credential_saved:
            operation, credential = self.personal_credential_saved
            try:
                record_personal_credential_audit(
                    operation=operation,
                    result='success',
                    user=self.request.user,
                    credential=credential,
                )
            except Exception:
                logger.exception(
                    'Record personal credential success audit failed'
                )
        return response


class SuperConnectionTokenViewSet(ConnectionTokenViewSet):
    serializer_classes = {
        'default': SuperConnectionTokenSerializer,
        'get_secret_detail': ConnectionTokenSecretSerializer,
    }
    rbac_perms = {
        'create': 'authentication.add_superconnectiontoken',
        'renewal': 'authentication.add_superconnectiontoken',
        'list': 'authentication.view_superconnectiontoken',
        'check': 'authentication.view_superconnectiontoken',
        'retrieve': 'authentication.view_superconnectiontoken',
        'acl_controls': 'authentication.add_superconnectiontoken',
        'get_secret_detail': 'authentication.view_superconnectiontokensecret',
        'get_applet_info': 'authentication.view_superconnectiontoken',
        'release_applet_account': 'authentication.view_superconnectiontoken',
        'get_virtual_app_info': 'authentication.view_superconnectiontoken',
    }

    def get_queryset(self):
        return ConnectionToken.objects.none()

    def get_object(self):
        pk = self.kwargs.get(self.lookup_field)
        token = get_object_or_404(
            ConnectionToken.objects.select_related(
                'user', 'asset__platform'
            ),
            pk=pk,
        )
        return token

    def get_user(self, serializer):
        return serializer.validated_data.get('user')

    @action(methods=['GET'], detail=True, url_path='check')
    def check(self, request, *args, **kwargs):
        instance = self.get_object()
        data = {
            "detail": "OK",
            "code": "perm_ok",
            "expired": instance.is_expired
        }
        try:
            # Components check established sessions after the one-time token
            # has been consumed. Revalidate access without reviving that token.
            instance.is_valid(check_expiration=False)
            if not instance.personal_credential_id:
                self._validate_perm(
                    instance.user,
                    instance.asset,
                    instance.account,
                    instance.protocol,
                    token_type=instance.type,
                )
        except JMSException as e:
            data['code'] = e.detail.code
            data['detail'] = str(e.detail)
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        except APIException as error:
            data['code'] = get_personal_credential_failure_reason(error)
            data['detail'] = str(error.detail)
            record_connection_token_credential_audit(instance, result='failed', error=error)
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)

        return Response(data=data, status=status.HTTP_200_OK)

    @action(methods=['PATCH'], detail=False)
    def renewal(self, request, *args, **kwargs):
        from common.utils.timezone import as_current_tz

        token_id = request.data.get('id') or ''
        token = get_object_or_404(ConnectionToken, pk=token_id)
        date_expired = as_current_tz(token.date_expired)
        if token.is_expired:
            raise PermissionDenied(gettext('Token is expired at: {}').format(date_expired))
        token.renewal()
        data = {
            'ok': True,
            'msg': f'Token is renewed, date expired: {date_expired}'
        }
        return Response(data=data, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='secret')
    def get_secret_detail(self, request, *args, **kwargs):
        """ 非常重要的 api, 在逻辑层再判断一下 rbac 权限, 双重保险 """
        rbac_perm = 'authentication.view_superconnectiontokensecret'
        if not request.user.has_perm(rbac_perm):
            raise PermissionDenied(gettext('Not allow to view secret'))

        from .rdp_login import is_tinker
        if is_tinker(request.user):
            raise PermissionDenied(gettext('Tinker must redeem its RDP login ticket to obtain credentials'))

        token_id = request.data.get('id') or ''
        token = ConnectionToken.get_typed_connection_token(token_id)
        if not token:
            raise PermissionDenied(gettext('Token {} is not valid').format(token))
        return Response(get_connection_token_secret(
            token, self.get_serializer,
            expire_now=request.data.get('expire_now', True),
            public_key=request.data.get('public_key', ''),
        ))

    @action(methods=['POST'], detail=False, url_path='applet-option')
    def get_applet_info(self, request, *args, **kwargs):
        from .rdp_login import issue_applet_ticket, private_response
        from ..serializers.rdp_login import NonzeroUUIDField

        user = request.user
        terminal = getattr(user, 'terminal', None)
        if (not user.is_service_account or not terminal
                or terminal.type not in ('razor', 'koko', 'lion')
                or not user.has_perm('authentication.view_superconnectiontoken')):
            raise PermissionDenied()
        token_id = NonzeroUUIDField().run_validation(request.data.get('id'))
        with transaction.atomic(), tmp_to_root_org():
            token = ConnectionToken.get_typed_connection_token(token_id)
            if token is None:
                raise PermissionDenied(gettext('Invalid connection token'))
            data = issue_applet_ticket(token)
            return private_response(ConnectTokenAppletOptionSerializer(data).data)

    @action(methods=['POST'], detail=False, url_path='virtual-app-option')
    def get_virtual_app_info(self, *args, **kwargs):
        token_id = self.request.data.get('id')
        token = get_object_or_404(ConnectionToken, pk=token_id)
        if token.is_expired:
            return Response({'error': gettext('Token expired')}, status=status.HTTP_400_BAD_REQUEST)
        data = token.get_virtual_app_option()
        serializer = ConnectTokenVirtualAppOptionSerializer(data)
        return Response(serializer.data)

    @action(methods=['DELETE', 'POST'], detail=False, url_path='applet-account/release')
    def release_applet_account(self, *args, **kwargs):
        # Older components still send this after disconnect. Account ownership
        # and safe reuse now follow the actual Windows session in Tinker.
        return Response({'msg': 'released'})


class AdminConnectionTokenViewSet(ConnectionTokenViewSet):
    serializer_classes = {
        'default': AdminConnectionTokenSerializer,
    }

    def check_permissions(self, request):
        user = request.user
        if not user.is_superuser:
            self.permission_denied(request)

    def get_queryset(self):
        return AdminConnectionToken.objects.all().filter(user=self.request.user)

    def get_permed_account(self, user, asset, account_name, protocol):
        return AdminConnectionToken.get_user_permed_account(user, asset, account_name, protocol)
