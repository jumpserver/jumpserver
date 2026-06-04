
import base64
import os
import subprocess
import tempfile
from django.utils.translation import gettext_lazy as _

import yaml
from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from common.permissions import OnlySuperUser
from common.utils import get_logger
from .sdk import ukey_sdk_config
from .utils import is_sm2_pem


__all__ = ['UKeySDKScriptFileAPIView', 'UKeySDKConfigFileAPIView']

logger = get_logger(__name__)


class UKeySDKScriptFileAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        content = ukey_sdk_config.load_sdk_script_content()
        if content is None:
            raise Http404
        return HttpResponse(content, content_type='application/javascript')


class UKeySDKConfigFileAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        lang = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME) or settings.LANGUAGE_CODE
        data = ukey_sdk_config.get_sdk_config(lang=lang)
        return Response(data)


class UKeyCertEnrollAPIView(APIView):
    rbac_perms = {
        'POST': 'users.change_user',
    }

    def post(self, request):
        if not ukey_sdk_config.enroll_enabled:
            data = {'error': _('Certificate enrollment is not enabled')}
            return Response(data=data, status=400)

        csr_raw = request.data.get('csr')
        if not csr_raw:
            data = {'error': _('CSR is required')}
            return Response(data=data, status=400)

        try:
            singed_cert = self.sign_cert(csr_raw)
        except Exception as e:
            error = '{}: {}'.format(_('Certificate signing failed'), str(e))
            logger.error(error, exc_info=True)
            return Response(data={'error': error}, status=400)

        data = {'signed_cert': singed_cert}
        return Response(data=data, status=200)

    def sign_cert(self, csr_raw):
        # 记录输入是否含 PEM 头，用于决定输出格式
        if isinstance(csr_raw, bytes):
            has_pem_header = csr_raw.lstrip().startswith(b'-----BEGIN')
        else:
            has_pem_header = csr_raw.strip().startswith('-----BEGIN')

        csr_pem = self._normalize_csr_to_pem(csr_raw)
        if self._is_sm2_csr(csr_pem):
            singed_cert = self.sign_cert_by_gmssl(csr_pem)
        else:
            singed_cert = self.sign_cert_by_other(csr_pem)

        # 输入不含 PEM 头时，返回裸 base64（去掉首尾标识行）
        if not has_pem_header:
            lines = singed_cert.strip().splitlines()
            singed_cert = ''.join(
                ln for ln in lines if not ln.startswith('-----')
            )
        return singed_cert

    def _normalize_csr_to_pem(self, csr_data):
        """
        将 SDK 返回的 CSR 统一转换成标准 PEM 字符串。
        支持三种输入格式：
          1. 已经是标准 PEM（含 -----BEGIN CERTIFICATE REQUEST----- 头）
          2. 裸 base64 字符串（无 PEM 头，国密 USB Key SDK 常见）
          3. 原始 DER 二进制 bytes
        """
        if isinstance(csr_data, bytes):
            if csr_data.lstrip().startswith(b'-----BEGIN'):
                return csr_data.decode('utf-8')
            b64 = base64.b64encode(csr_data).decode('ascii')
        else:
            csr_data = csr_data.strip()
            if csr_data.startswith('-----BEGIN'):
                return csr_data
            # 裸 base64：去除空白后校验并重新分行
            b64 = ''.join(csr_data.split())
            base64.b64decode(b64, validate=True)

        lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
        return (
            '-----BEGIN CERTIFICATE REQUEST-----\n'
            + '\n'.join(lines)
            + '\n-----END CERTIFICATE REQUEST-----\n'
        )

    def _is_sm2_csr(self, csr_pem):
        """通过查找 SM2 曲线 OID 字节序列判断 CSR 是否使用 SM2 算法。"""
        return is_sm2_pem(csr_pem)

    def sign_cert_by_other(self, csr_pem):
        import datetime
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec, rsa

        csr = x509.load_pem_x509_csr(csr_pem.encode())
        pub_key = csr.public_key()

        if isinstance(pub_key, ec.EllipticCurvePublicKey):
            raise NotImplementedError('ECDSA certificate signing is not supported')
        if not isinstance(pub_key, rsa.RSAPublicKey):
            raise ValueError('Unsupported key type: {}'.format(type(pub_key).__name__))

        ca_key_content = ukey_sdk_config.ca_key_content
        ca_cert_content = ukey_sdk_config.ca_cert_content
        ca_key_pass = ukey_sdk_config.ca_key_pass
        if not ca_key_content:
            raise ValueError('AUTH_UKEY_CA_KEY_CONTENT not configured')
        if not ca_cert_content:
            raise ValueError('AUTH_UKEY_CA_CERT_CONTENT not configured')

        ca_cert = x509.load_pem_x509_certificate(ca_cert_content.encode())
        password = ca_key_pass.encode() if ca_key_pass else None
        ca_key = serialization.load_pem_private_key(ca_key_content.encode(), password=password)

        validity_days = ukey_sdk_config.enroll_validity_days
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(csr.subject)
            .issuer_name(ca_cert.subject)
            .public_key(pub_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(ca_key, hashes.SHA256())
        )
        return cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

    def sign_cert_by_gmssl(self, csr_pem):
        """
        使用 gmssl reqsign 签发 SM2 证书。
        命令示例：
          gmssl reqsign -in user.csr -days 365 -cacert root.crt -key root.key -pass 123456 -out user.crt
        """
        gmssl_bin = ukey_sdk_config.gmssl_bin
        ca_key_content = ukey_sdk_config.ca_key_content
        ca_cert_content = ukey_sdk_config.ca_cert_content
        ca_key_pass = ukey_sdk_config.ca_key_pass
        if not ca_key_content:
            raise ValueError('AUTH_UKEY_CA_KEY_CONTENT not configured')
        if not ca_cert_content:
            raise ValueError('AUTH_UKEY_CA_CERT_CONTENT not configured')

        validity_days = str(ukey_sdk_config.enroll_validity_days)

        csr_file = ca_cert_file = ca_key_file = cert_file = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix='.csr', mode='w', delete=False, encoding='utf-8'
            ) as f:
                f.write(csr_pem)
                csr_file = f.name

            with tempfile.NamedTemporaryFile(
                suffix='.crt', mode='w', delete=False, encoding='utf-8'
            ) as f:
                f.write(ca_cert_content)
                ca_cert_file = f.name

            with tempfile.NamedTemporaryFile(
                suffix='.key', mode='w', delete=False, encoding='utf-8'
            ) as f:
                f.write(ca_key_content)
                ca_key_file = f.name

            fd, cert_file = tempfile.mkstemp(suffix='.crt')
            os.close(fd)

            # https://github.com/GmSSL/GmSSL-Python#sm2数字证书
            # gmssl_python 只支持SM2证书的解析和验证等功能，不支持SM2证书的签发和生成，
            # 所以还是需要使用 gmssl bin 来执行 reqsign 命令行工具进行签发。虽然增加了对外部命令的依赖，
            # 但这是目前最简单可靠的方案。
            cmd = [
                gmssl_bin, 'reqsign',
                '-in', csr_file,
                '-days', validity_days,
                '-cacert', ca_cert_file,
                '-key', ca_key_file,
                '-out', cert_file,
            ]
            if ca_key_pass:
                cmd += ['-pass', ca_key_pass]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                raise RuntimeError('gmssl reqsign failed: {}'.format(result.stderr.strip()))

            with open(cert_file, 'r', encoding='utf-8') as f:
                return f.read()
        finally:
            for path in (csr_file, ca_cert_file, ca_key_file, cert_file):
                if path and os.path.exists(path):
                    os.unlink(path)
