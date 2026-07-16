import base64
import json
import os
import urllib.parse
from struct import pack

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.const import AliasAccount
from accounts.utils import validate_account_username
from acls.notifications import AssetLoginReminderMsg
from common.api import JMSModelViewSet
from common.exceptions import JMSException
from common.utils import random_string, get_logger, get_request_ip_or_data
from common.utils.django import get_request_os
from common.utils.http import is_true, is_false
from orgs.mixins.api import RootOrgViewMixin
from orgs.utils import tmp_to_org
from perms.models import ActionChoices
from terminal.connect_methods import NativeClient, ConnectMethodUtil, WebMethod
from terminal.models import EndpointRule, Endpoint
from users.const import FileNameConflictResolution
from users.const import RDPSmartSize, RDPColorQuality
from users.models import Preference
from .face import FaceMonitorContext
from ..mixins import AuthFaceMixin
from ..models import ConnectionToken, AdminConnectionToken, date_expired_default
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
        # 设置多屏显示
        multi_mon = is_true(self.request.query_params.get('multi_mon'))
        if multi_mon:
            rdp_options['use multimon:i'] = '1'

        # 设置磁盘挂载
        drives_redirect = is_true(self.request.query_params.get('drives_redirect'))
        if drives_redirect:
            if ActionChoices.contains(token.actions, ActionChoices.transfer()):
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

        resolution_value = token.connect_options.get('resolution', 'auto')
        if resolution_value != 'auto':
            width, height = resolution_value.split('x')
            if width and height:
                rdp_options['desktopwidth:i'] = width
                rdp_options['desktopheight:i'] = height
                rdp_options['winposstr:s'] = f'0,1,0,0,{width},{height}'
                rdp_options['dynamic resolution:i'] = '0'

        color_quality = self.request.query_params.get('rdp_color_quality')
        color_quality = color_quality if color_quality else os.getenv('JUMPSERVER_COLOR_DEPTH', RDPColorQuality.HIGH)

        # 设置其他选项
        rdp_options['session bpp:i'] = color_quality
        rdp_options['audiomode:i'] = self.parse_env_bool('JUMPSERVER_DISABLE_AUDIO', 'false', '2', '0')
        rdp_options['smart sizing:i'] = self.request.query_params.get('rdp_smart_size', RDPSmartSize.DISABLE)

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
    def get_token_account_display(token):  #新增方法
            try:
                account = token.account_object
            except Exception:
                account = None
            if account:
                return account.full_username or account.username or account.name or token.account
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
            'token': {
                'id': str(token.id),
                'value': token.value,
            },
            'file': {},
            'command': ''
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
            'url': 'jms://{}'.format(protocol_data)
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
    def exchange(self, request, *args, **kwargs):
        pk = request.data.get('id', None) or request.data.get('pk', None)
        # 只能兑换自己使用的 Token
        instance = get_object_or_404(ConnectionToken, pk=pk, user=request.user)
        instance.id = None
        self.validate_exchange_token(instance)
        instance.date_expired = date_expired_default()
        instance.save()
        serializer = self.get_serializer(instance)
        response = Response(serializer.data, status=status.HTTP_201_CREATED)
        if self.need_face_verify:
            self.create_face_verify(response)
        return response


class ConnectionTokenViewSet(AuthFaceMixin, ExtraActionApiMixin, RootOrgViewMixin, JMSModelViewSet):
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
        'reuse': 'authentication.reuse_connectiontoken',
        'expire': 'authentication.expire_connectiontoken',
        'get_rdp_file': 'authentication.add_connectiontoken',
        'get_client_protocol_url': 'authentication.add_connectiontoken',
    }
    input_username = ''
    need_face_verify = False
    face_monitor_token = ''

    def get_queryset(self):
        queryset = ConnectionToken.objects \
            .filter(user=self.request.user) \
            .filter(date_expired__gt=timezone.now())
        return queryset

    def get_user(self, serializer):
        return self.request.user

    def perform_create(self, serializer):
        self.validate_serializer(serializer)
        return super().perform_create(serializer)


    def _insert_connect_options(self, data, user):
        connect_options = data.pop('connect_options', {})
        default_name_opts = {
            'file_name_conflict_resolution': FileNameConflictResolution.REPLACE,
            'terminal_theme_name': 'Default',
        }
        preferences_query = Preference.objects.filter(
            user=user, category='luna', name__in=default_name_opts.keys()
        ).values_list('name', 'value')
        preferences = dict(preferences_query)
        for name in default_name_opts.keys():
            value = preferences.get(name, default_name_opts[name])
            connect_options[name] = value
        connect_options['lang'] = getattr(user, 'lang') or settings.LANGUAGE_CODE
        data['connect_options'] = connect_options

    @staticmethod
    def get_input_username(data):
        input_username = data.get('input_username', '')
        if input_username:
            return input_username

        account = data.get('account', '')
        if account == '@USER':
            input_username = str(data.get('user', ''))
        elif account == '@INPUT':
            input_username = '@INPUT'
        else:
            input_username = account
        return input_username

    def validate_serializer(self, serializer):
        data = serializer.validated_data
        user = self.get_user(serializer)
        self._insert_connect_options(data, user)
        asset = data.get('asset')
        account_name = data.get('account')
        protocol = data.get('protocol')
        connect_method = data.get('connect_method')
        self.input_username = self.get_input_username(data)
        if account_name == AliasAccount.INPUT:
            # Manual account input can reach Luna directly, so validate before ACL/token creation.
            self.input_username = validate_account_username(self.input_username)
            data['input_username'] = self.input_username
        _data = self._validate(user, asset, account_name, protocol, connect_method)
        data.update(_data)
        return serializer

    def validate_exchange_token(self, token):
        user = token.user
        asset = token.asset
        account_alias = token.account
        _data = self._validate(user, asset, account_alias, token.protocol, token.connect_method)
        for k, v in _data.items():
            setattr(token, k, v)
        return token

    def _validate(self, user, asset, account_alias, protocol, connect_method):
        data = dict()
        data['org_id'] = asset.org_id
        data['user'] = user
        data['value'] = random_string(16)

        if account_alias == AliasAccount.ANON and asset.category not in ['web', 'custom']:
            raise ValidationError(_('Anonymous account is not supported for this asset'))

        account = self._validate_perm(user, asset, account_alias, protocol)
        if account.has_secret:
            data['input_secret'] = ''
            data['input_secret_type'] = account.secret_type

        if account_alias != AliasAccount.INPUT and account_alias != AliasAccount.USER:
            data['input_username'] = ''
            data['input_secret_type'] = ''

        ticket = self._validate_acl(user, asset, account, connect_method, protocol)
        if ticket:
            data['from_ticket'] = ticket

        if ticket or self.need_face_verify:
            data['is_active'] = False
        if self.face_monitor_token:
            FaceMonitorContext.get_or_create_context(self.face_monitor_token, self.request.user.id)
            data['face_monitor_token'] = self.face_monitor_token
        return data

    @staticmethod
    def get_permed_account(user, asset, account_alias, protocol):
        return ConnectionToken.get_user_permed_account(user, asset, account_alias, protocol)

    def _validate_perm(self, user, asset, account_alias, protocol):
        account = self.get_permed_account(user, asset, account_alias, protocol)
        if not account or not account.actions:
            msg = _('Account not found')
            raise JMSException(code='perm_account_invalid', detail=msg)
        if account.date_expired < timezone.now():
            msg = _('Permission expired')
            raise JMSException(code='perm_expired', detail=msg)
        return account

    def _record_operate_log(self, acl, asset):
        from audits.handler import create_or_update_operate_log
        with tmp_to_org(asset.org_id):
            after = {
                str(_('Assets')): str(asset),
                str(_('Account')): self.input_username
            }
            object_name = acl._meta.object_name
            resource_type = acl._meta.verbose_name
            create_or_update_operate_log(
                acl.action, resource_type, resource=acl,
                after=after, object_name=object_name
            )

    def _validate_acl(self, user, asset, account, connect_method, protocol):
        from acls.models import LoginAssetACL
        kwargs = {'user': user, 'asset': asset, 'account': account}
        if account.username == AliasAccount.INPUT:
            kwargs['account_username'] = self.input_username
        acls = LoginAssetACL.filter_queryset(**kwargs)
        ip = get_request_ip_or_data(self.request)
        acl = LoginAssetACL.get_match_rule_acls(user, ip, acls)
        if not acl:
            return
        if acl.is_action(acl.ActionChoices.accept):
            self._record_operate_log(acl, asset)
            return
        if acl.is_action(acl.ActionChoices.reject):
            self._record_operate_log(acl, asset)
            msg = _('ACL action is reject: {}({})'.format(acl.name, acl.id))
            raise JMSException(code='acl_reject', detail=msg)
        if acl.is_action(acl.ActionChoices.review):
            if not self.request.query_params.get('create_ticket'):
                msg = _('ACL action is review')
                raise JMSException(code='acl_review', detail=msg)
            self._record_operate_log(acl, asset)
            ticket = LoginAssetACL.create_login_asset_review_ticket(
                user=user, asset=asset, account_username=self.input_username,
                assignees=acl.reviewers.all(), org_id=asset.org_id
            )
            return ticket
        if acl.is_action(acl.ActionChoices.face_verify):
            if not self.request.query_params.get('face_verify'):
                msg = _('ACL action is face verify')
                raise JMSException(code='acl_face_verify', detail=msg)
            self.need_face_verify = True
        if acl.is_action(acl.ActionChoices.face_online):
            if connect_method not in [WebMethod.web_cli, WebMethod.web_gui]:
                msg = _('ACL action not supported for this asset')
                raise JMSException(detail=msg, code='acl_face_online_not_supported')

            face_verify = self.request.query_params.get('face_verify')
            face_monitor_token = self.request.query_params.get('face_monitor_token')

            if not face_verify or not face_monitor_token:
                msg = _('ACL action is face online')
                raise JMSException(code='acl_face_online', detail=msg)

            self.need_face_verify = True
            self.face_monitor_token = face_monitor_token

        if acl.is_action(acl.ActionChoices.notice):
            reviewers = acl.reviewers.all()
            if not reviewers:
                return

            self._record_operate_log(acl, asset)
            os = get_request_os(self.request) if self.request else 'windows'
            method = ConnectMethodUtil.get_connect_method(
                connect_method, protocol=protocol, os=os
            )
            login_from = method['label'] if method else connect_method
            for reviewer in reviewers:
                AssetLoginReminderMsg(
                    reviewer, asset, user, account, acl,
                    ip, self.input_username, login_from
                ).publish_async()

    def create_face_verify(self, response):
        if not self.request.user.face_vector:
            raise JMSException(code='no_face_feature', detail=_('No available face feature'))
        connection_token_id = response.data.get('id')
        context_data = {
            "action": "login_asset",
            "connection_token_id": connection_token_id,
        }
        face_verify_token = self.create_face_verify_context(context_data)
        response.data['face_token'] = face_verify_token

    @staticmethod
    def format_validation_error(detail):
        # Luna renders detail directly and cannot display DRF field-error dicts cleanly.
        if isinstance(detail, dict):
            errors = []
            for messages in detail.values():
                if isinstance(messages, (list, tuple)):
                    messages = ', '.join([str(message) for message in messages])
                errors.append(str(messages))
            return '; '.join(errors)
        if isinstance(detail, (list, tuple)):
            return '; '.join([str(item) for item in detail])
        return str(detail)

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            if self.need_face_verify:
                self.create_face_verify(response)
        except JMSException as e:
            data = {'code': e.detail.code, 'detail': e.detail}
            return Response(data, status=e.status_code)
        except ValidationError as e:
            data = {'detail': self.format_validation_error(e.detail)}
            return Response(data, status=e.status_code)
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
        'get_secret_detail': 'authentication.view_superconnectiontokensecret',
        'get_applet_info': 'authentication.view_superconnectiontoken',
        'release_applet_account': 'authentication.view_superconnectiontoken',
        'get_virtual_app_info': 'authentication.view_superconnectiontoken',
    }

    def get_queryset(self):
        return ConnectionToken.objects.none()

    def get_object(self):
        pk = self.kwargs.get(self.lookup_field)
        token = get_object_or_404(ConnectionToken, pk=pk)
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
            self._validate_perm(
                instance.user,
                instance.asset,
                instance.account,
                instance.protocol
            )
        except JMSException as e:
            data['code'] = e.detail.code
            data['detail'] = str(e.detail)
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)

        return Response(data=data, status=status.HTTP_200_OK)

    @action(methods=['PATCH'], detail=False)
    def renewal(self, request, *args, **kwargs):
        from common.utils.timezone import as_current_tz

        token_id = request.data.get('id') or ''
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

    @action(methods=['POST'], detail=False, url_path='secret')
    def get_secret_detail(self, request, *args, **kwargs):
        """ 非常重要的 api, 在逻辑层再判断一下 rbac 权限, 双重保险 """
        rbac_perm = 'authentication.view_superconnectiontokensecret'
        if not request.user.has_perm(rbac_perm):
            raise PermissionDenied('Not allow to view secret')

        token_id = request.data.get('id') or ''
        token = ConnectionToken.get_typed_connection_token(token_id)
        if not token:
            raise PermissionDenied('Token {} is not valid'.format(token))
        token.is_valid()
        serializer = self.get_serializer(instance=token)

        expire_now = request.data.get('expire_now', True)
        asset_type = token.asset.type
        # 设置默认值
        if asset_type in ['k8s', 'kubernetes']:
            expire_now = False

        if token.is_reusable and settings.CONNECTION_TOKEN_REUSABLE:
            logger.debug('Token is reusable, not expire now')
        elif is_false(expire_now):
            logger.debug('Api specified, now expire now')
        else:
            token.expire()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='applet-option')
    def get_applet_info(self, *args, **kwargs):
        token_id = self.request.data.get('id')
        token = get_object_or_404(ConnectionToken, pk=token_id)
        if token.is_expired:
            return Response({'error': 'Token expired'}, status=status.HTTP_400_BAD_REQUEST)
        data = token.get_applet_option()
        serializer = ConnectTokenAppletOptionSerializer(data)
        return Response(serializer.data)

    @action(methods=['POST'], detail=False, url_path='virtual-app-option')
    def get_virtual_app_info(self, *args, **kwargs):
        token_id = self.request.data.get('id')
        token = get_object_or_404(ConnectionToken, pk=token_id)
        if token.is_expired:
            return Response({'error': 'Token expired'}, status=status.HTTP_400_BAD_REQUEST)
        data = token.get_virtual_app_option()
        serializer = ConnectTokenVirtualAppOptionSerializer(data)
        return Response(serializer.data)

    @action(methods=['DELETE', 'POST'], detail=False, url_path='applet-account/release')
    def release_applet_account(self, *args, **kwargs):
        lock_key = self.request.data.get('id')
        released = ConnectionToken.release_applet_account(lock_key)

        if released:
            logger.debug('Release applet account success: {}'.format(lock_key))
            return Response({'msg': 'released'})
        else:
            logger.error('Release applet account error: {}'.format(lock_key))
            return Response({'error': 'not found or expired'}, status=400)


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
