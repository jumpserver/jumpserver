
import base64
import os
import subprocess
import tempfile

import yaml
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.response import Response
from rest_framework.views import APIView
from common.permissions import OnlySuperUser
from common.utils import get_logger



__all__ = ['VendorDriverFileAPIView', 'CertVendorDriverConfigAPIView']

logger = get_logger(__name__)


class VendorDriverFileAPIView(APIView):
    permission_classes = (OnlySuperUser,)

    def get(self, request):
        js_file = getattr(settings, 'AUTH_CERT_VENDOR_DRIVER_FILE', None)
        if not js_file or not os.path.isfile(js_file):
            raise Http404
        return FileResponse(open(js_file, 'rb'), content_type='application/javascript')


class CertVendorDriverConfigAPIView(APIView):
    permission_classes = (OnlySuperUser,)

    def get(self, request):
        config_file = getattr(settings, 'AUTH_CERT_VENDOR_DRIVER_CONFIG_FILE', None)
        if not config_file or not os.path.isfile(config_file):
            raise Http404
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return Response(data)


class CertEnrollAPIView(APIView):
    permission_classes = (OnlySuperUser,)

    def post(self, request):
        csr_raw = request.data.get('csr')
        if not csr_raw:
            return Response(data={'error': 'CSR is required'}, status=400)
        try:
            csr_pem = self._normalize_csr_to_pem(csr_raw)
            signed_cert = self._sign_csr_with_openssl(csr_pem)
        except Exception as e:
            logger.error("Certificate enrollment failed, error: {}".format(str(e)))
            return Response(data={'error': str(e)}, status=400)
        else:
            return Response(data={'signed_cert': signed_cert}, status=200)

    def _normalize_csr_to_pem(self, csr_data):
        """
        将 USB Key SDK 返回的 CSR 统一转换为 PEM 字符串。
        SDK 可能返回三种格式：
          1. 标准 PEM（含 -----BEGIN CERTIFICATE REQUEST----- 头）
          2. 裸 base64 字符串（无 PEM 头，国密 SDK 常见）
          3. 原始 DER 二进制 bytes
        """
        if isinstance(csr_data, bytes):
            # bytes：先判断是否已是 PEM，否则当作 DER 转 PEM
            if csr_data.lstrip().startswith(b'-----BEGIN'):
                return csr_data.decode('utf-8')
            b64 = base64.b64encode(csr_data).decode('ascii')
        else:
            csr_data = csr_data.strip()
            if csr_data.startswith('-----BEGIN'):
                return csr_data
            # 裸 base64：去除所有空白后重新分行
            b64 = ''.join(csr_data.split())
            # 校验是否合法 base64
            base64.b64decode(b64, validate=True)

        # 以 64 字符为一行，包装成 PEM
        lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
        return (
            '-----BEGIN CERTIFICATE REQUEST-----\n'
            + '\n'.join(lines)
            + '\n-----END CERTIFICATE REQUEST-----\n'
        )

    def _extract_spki_pem_from_csr_pem(self, csr_pem):
        """
        从 CSR PEM 中直接提取 SubjectPublicKeyInfo，不验证 CSR 自签名。
        国密 USB Key SDK 生成的 SM2 CSR 的自签名 SM2-ID 与 OpenSSL 验证时使用的不一致，
        会导致 OpenSSL 3.x 拒绝签发（"CSR self-signature does not match"）。
        用 -force_pubkey 提供公钥后 OpenSSL 会跳过自签名校验。

        PKCS#10 DER 结构:
          SEQUENCE (CertificationRequest)
            SEQUENCE (CertificationRequestInfo)
              INTEGER (version)
              SEQUENCE (subject)
              SEQUENCE (subjectPublicKeyInfo)  ← 目标
              [0] (attributes)
            SEQUENCE (signatureAlgorithm)
            BIT STRING (signature)
        """
        pem_lines = csr_pem.strip().splitlines()
        b64 = ''.join(ln for ln in pem_lines if not ln.startswith('-----'))
        der = base64.b64decode(b64)

        def read_tlv(data, pos):
            """返回 (value_start, value_end)，不校验 tag。"""
            pos += 1  # skip tag byte
            lb = data[pos]; pos += 1
            if lb & 0x80:
                n = lb & 0x7f
                length = int.from_bytes(data[pos:pos + n], 'big')
                pos += n
            else:
                length = lb
            return pos, pos + length

        # Enter CertificationRequest SEQUENCE
        vstart, _ = read_tlv(der, 0)
        pos = vstart

        # Enter CertificationRequestInfo SEQUENCE
        vstart, _ = read_tlv(der, pos)
        pos = vstart

        # Skip version INTEGER
        _, vend = read_tlv(der, pos)
        pos = vend

        # Skip subject SEQUENCE
        _, vend = read_tlv(der, pos)
        pos = vend

        # Capture subjectPublicKeyInfo TLV (包含 tag 本身)
        spki_start = pos
        _, vend = read_tlv(der, pos)
        spki_der = der[spki_start:vend]

        b64_spki = base64.b64encode(spki_der).decode('ascii')
        lines = [b64_spki[i:i + 64] for i in range(0, len(b64_spki), 64)]
        return '-----BEGIN PUBLIC KEY-----\n' + '\n'.join(lines) + '\n-----END PUBLIC KEY-----\n'

    def _sign_csr_with_openssl(self, csr_pem):
        """
        调用 OpenSSL CLI 签发证书，完整支持 SM2/SM3（cryptography 库 Python API 不支持）。
        使用 -force_pubkey 绕过 OpenSSL 3.x 对 SM2 CSR 自签名的严格校验。
        # openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:SM2 -out ca_key.pem
        # openssl req -new -x509 -key ca_key.pem -out ca_cert.pem -days 3650 -subj "/C=CN/O=JumpServer/CN=JumpServer Root CA"
        """
        ca_key_path = getattr(settings, 'CA_KEY_FILE', None)
        ca_cert_path = getattr(settings, 'CA_CERT_FILE', None)
        if not ca_key_path or not os.path.isfile(ca_key_path):
            raise FileNotFoundError('CA_KEY_FILE not configured or not found')
        if not ca_cert_path or not os.path.isfile(ca_cert_path):
            raise FileNotFoundError('CA_CERT_FILE not configured or not found')

        validity_days = str(getattr(settings, 'AUTH_CERT_ENROLL_VALIDITY_DAYS', 365))
        pubkey_pem = self._extract_spki_pem_from_csr_pem(csr_pem)

        csr_file = pubkey_file = cert_file = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix='.csr', mode='w', delete=False, encoding='utf-8'
            ) as f:
                f.write(csr_pem)
                csr_file = f.name

            with tempfile.NamedTemporaryFile(
                suffix='.pub.pem', mode='w', delete=False, encoding='utf-8'
            ) as f:
                f.write(pubkey_pem)
                pubkey_file = f.name

            fd, cert_file = tempfile.mkstemp(suffix='.crt')
            os.close(fd)

            result = subprocess.run(
                [
                    'openssl', 'x509', '-req',
                    '-in', csr_file,
                    '-force_pubkey', pubkey_file,   # 提供公钥并跳过 CSR 自签名校验
                    '-CA', ca_cert_path,
                    '-CAkey', ca_key_path,
                    '-CAcreateserial',
                    '-out', cert_file,
                    '-days', validity_days,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError('OpenSSL signing failed: {}'.format(result.stderr.strip()))

            with open(cert_file, 'r', encoding='utf-8') as f:
                return f.read()
        finally:
            for path in (csr_file, pubkey_file, cert_file):
                if path and os.path.exists(path):
                    os.unlink(path)