# -*- coding: utf-8 -*-
#

import base64
import os
import tempfile

from django.conf import settings
from django.core.exceptions import PermissionDenied

from users.models import User
from common.utils import get_logger
from ..base import JMSBaseAuthBackend
from .driver import cert_vd_cfg
from .exceptions import (
    CertAuthError,
    CertUserNotFoundError,
    CertUkeySNMismatchError,
    CertNormalizationError,
    CertChainError,
    CertCNMismatchError,
    CertSignatureError,
    CertUnsupportedAlgorithmError,
)
from .utils import is_sm2_pem


__all__ = ['CertBackend']

logger = get_logger(__name__)


class CertBackend(JMSBaseAuthBackend):
    backend = settings.AUTH_BACKEND_CERT

    @staticmethod
    def is_enabled():
        return settings.AUTH_CERT

    # ── 主入口 ────────────────────────────────────────────────────────────────

    def authenticate(self, request, username, cert, signature, challenge, ukey_sn=None):
        try:
            user = self._check_user_and_ukey_sn(username, ukey_sn)
            cert_pem = self._load_cert_pem(cert)
            if self._is_sm2_cert(cert_pem):
                return self._authenticate_sm2(cert_pem, username, signature, challenge, user)
            else:
                return self._authenticate_other(cert_pem, username, signature, challenge, user)
        except CertAuthError as e:
            if request:
                request.error_message = str(e)
            raise PermissionDenied(str(e))

    # ── Part 1: 用户与 UKey SN 预校验 ────────────────────────────────────────

    def _check_user_and_ukey_sn(self, username, ukey_sn):
        """查找用户并校验 ukey_sn 绑定关系，返回 User 实例。"""
        ukey_sn = (ukey_sn or '').strip()
        user = User.objects.filter(username=username).first()
        if user is None:
            logger.warning('CertBackend: user %r not found', username)
            raise CertUserNotFoundError()
        if user.ukey_sn and ukey_sn != user.ukey_sn:
            logger.warning('CertBackend: ukey_sn mismatch for user %r', username)
            raise CertUkeySNMismatchError()
        return user

    # ── Part 2: SM2 证书校验流程 ──────────────────────────────────────────────

    def _authenticate_sm2(self, cert_pem, username, signature, challenge, user):
        """SM2 证书校验：加载 → 链校验 → CN 比对 → 签名验证。"""
        sm2_cert = self._load_sm2_cert(cert_pem)
        self._verify_sm2_cert_chain(sm2_cert)
        self._verify_cert_cn(sm2_cert.get_subject().get('commonName'), username)
        self._verify_sm2_signature(sm2_cert.get_subject_public_key(), signature, challenge)
        return user

    @staticmethod
    def _load_sm2_cert(cert_pem):
        """将 PEM 字符串写入临时文件，加载为 Sm2Certificate 对象后立即删除临时文件。"""
        from common.utils.gmssl_python import Sm2Certificate

        fd, cert_file = tempfile.mkstemp(suffix='.crt')
        try:
            os.close(fd)
            with open(cert_file, 'w', encoding='utf-8') as f:
                f.write(cert_pem)
            sm2_cert = Sm2Certificate()
            sm2_cert.import_pem(cert_file)
        except Exception as e:
            logger.warning('CertBackend: failed to load SM2 cert: %s', e)
            raise CertNormalizationError()
        finally:
            if os.path.exists(cert_file):
                os.unlink(cert_file)
        return sm2_cert

    @staticmethod
    def _verify_sm2_cert_chain(sm2_cert):
        """调用 Sm2Certificate.verify_by_ca_certificate 验证 SM2 证书链。"""
        from common.utils.gmssl_python import Sm2Certificate, SM2_DEFAULT_ID

        ca_cert_content = cert_vd_cfg.ca_cert_content
        if not ca_cert_content:
            raise CertChainError()

        fd, ca_cert_file = tempfile.mkstemp(suffix='.crt')
        try:
            os.close(fd)
            with open(ca_cert_file, 'w', encoding='utf-8') as f:
                f.write(ca_cert_content)
            ca_cert = Sm2Certificate()
            ca_cert.import_pem(ca_cert_file)
            ok = sm2_cert.verify_by_ca_certificate(ca_cert, SM2_DEFAULT_ID)
        except CertAuthError:
            raise
        except Exception as e:
            logger.warning('CertBackend: SM2 cert chain verification error: %s', e)
            raise CertChainError()
        finally:
            if os.path.exists(ca_cert_file):
                os.unlink(ca_cert_file)

        if not ok:
            logger.warning('CertBackend: SM2 cert chain verification failed')
            raise CertChainError()

    @staticmethod
    def _verify_sm2_signature(sm2_key, signature, challenge):
        """使用 gmssl_python 的 Sm2Signature 做 SM2withSM3 验签。"""
        from common.utils.gmssl_python import Sm2Signature, DO_VERIFY, SM2_DEFAULT_ID

        sig_bytes = CertBackend._decode_signature(signature)
        signed_data = CertBackend._challenge_as_bytes(challenge)
        try:
            verifier = Sm2Signature(sm2_key, SM2_DEFAULT_ID, DO_VERIFY)
            verifier.update(signed_data)
            ok = bool(verifier.verify(sig_bytes))
        except Exception as e:
            logger.warning('CertBackend: SM2 signature verification error: %s', e)
            raise CertSignatureError()
        if not ok:
            logger.warning('CertBackend: SM2 signature mismatch')
            raise CertSignatureError()

    # ── Part 3: RSA / 其他证书校验流程 ───────────────────────────────────────

    def _authenticate_other(self, cert_pem, username, signature, challenge, user):
        """RSA 证书校验：加载 → 链校验 → CN 比对 → 签名验证。"""
        cert, pub_key = self._load_rsa_cert(cert_pem)
        self._verify_rsa_cert_chain(cert)
        self._verify_cert_cn(self._extract_rsa_cert_cn(cert), username)
        self._verify_rsa_signature(pub_key, signature, challenge)
        return user

    @staticmethod
    def _load_rsa_cert(cert_pem):
        """加载 RSA PEM 证书，校验公钥算法类型，返回 (cert, pub_key)。"""
        from cryptography import x509
        from cryptography.hazmat.primitives.asymmetric import ec, rsa

        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode())
        except Exception as e:
            logger.warning('CertBackend: failed to load certificate: %s', e)
            raise CertNormalizationError()

        pub_key = cert.public_key()
        if isinstance(pub_key, ec.EllipticCurvePublicKey):
            logger.warning('CertBackend: ECDSA certificate verification is not supported')
            raise CertUnsupportedAlgorithmError()
        if not isinstance(pub_key, rsa.RSAPublicKey):
            logger.warning('CertBackend: unsupported key type: %s', type(pub_key).__name__)
            raise CertUnsupportedAlgorithmError()
        return cert, pub_key

    @staticmethod
    def _verify_rsa_cert_chain(cert):
        """使用 CA 根证书验证 RSA 证书链。"""
        from cryptography import x509
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import padding

        ca_cert_content = cert_vd_cfg.ca_cert_content
        if not ca_cert_content:
            logger.warning('CertBackend: AUTH_CERT_CA_CERT_CONTENT not configured')
            raise CertChainError()
        try:
            ca_cert = x509.load_pem_x509_certificate(ca_cert_content.encode())
            ca_cert.public_key().verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm,
            )
        except InvalidSignature:
            logger.warning('CertBackend: RSA cert chain verification failed')
            raise CertChainError()
        except CertAuthError:
            raise
        except Exception as e:
            logger.warning('CertBackend: RSA cert chain verification error: %s', e)
            raise CertChainError()

    @staticmethod
    def _extract_rsa_cert_cn(cert):
        """从 RSA 证书 subject 中提取 CN，失败时返回 None。"""
        from cryptography import x509

        try:
            return cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
        except Exception:
            return None

    @staticmethod
    def _verify_rsa_signature(pub_key, signature, challenge):
        """使用 RSA PKCS1v15 + SHA256 验证签名。"""
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        sig_bytes = CertBackend._decode_signature(signature)
        signed_data = CertBackend._challenge_as_bytes(challenge)
        try:
            pub_key.verify(sig_bytes, signed_data, padding.PKCS1v15(), hashes.SHA256())
        except InvalidSignature:
            logger.warning('CertBackend: RSA signature mismatch')
            raise CertSignatureError()
        except CertAuthError:
            raise
        except Exception as e:
            logger.warning('CertBackend: RSA signature verification error: %s', e)
            raise CertSignatureError()

    # ── 公共工具方法 ──────────────────────────────────────────────────────────

    @staticmethod
    def _verify_cert_cn(cert_cn, username):
        """校验证书 CN 与 username 是否匹配（SM2 和 RSA 流程共用）。"""
        if cert_cn != username:
            logger.warning(
                'CertBackend: cert CN %r does not match username %r', cert_cn, username
            )
            raise CertCNMismatchError()

    @staticmethod
    def _challenge_as_bytes(challenge):
        """将 challenge 统一转为 bytes（SM2 和 RSA 签名验证共用）。"""
        return challenge if isinstance(challenge, bytes) else challenge.encode('utf-8')

    @staticmethod
    def _load_cert_pem(cert_data):
        """将原始证书数据转为 PEM 字符串，格式不合法时抛出 CertNormalizationError。"""
        try:
            return CertBackend._normalize_cert_to_pem(cert_data)
        except Exception as e:
            logger.warning('CertBackend: cert normalization failed: %s', e)
            raise CertNormalizationError()

    @staticmethod
    def _is_sm2_cert(cert_pem):
        """通过 OID 字节序列判断证书是否使用 SM2 算法。"""
        return is_sm2_pem(cert_pem)

    @staticmethod
    def _normalize_cert_to_pem(cert_data):
        """
        将证书统一转换为标准 PEM 格式。
        支持：已含头尾的 PEM、裸 base64 字符串、DER bytes。
        """
        if isinstance(cert_data, bytes):
            if cert_data.lstrip().startswith(b'-----BEGIN'):
                return cert_data.decode('utf-8')
            b64 = base64.b64encode(cert_data).decode('ascii')
        else:
            cert_data = cert_data.strip()
            if cert_data.startswith('-----BEGIN'):
                return cert_data
            b64 = ''.join(cert_data.split())
            base64.b64decode(b64, validate=True)  # 验证是合法 base64

        lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
        return (
            '-----BEGIN CERTIFICATE-----\n'
            + '\n'.join(lines)
            + '\n-----END CERTIFICATE-----\n'
        )

    @staticmethod
    def _decode_signature(signature):
        """
        将签名值转为 bytes。
        依次尝试：已是 bytes → 十六进制字符串 → base64 字符串。
        """
        if isinstance(signature, bytes):
            return signature
        sig = signature.strip()
        try:
            return bytes.fromhex(sig)
        except ValueError:
            pass
        try:
            return base64.b64decode(sig)
        except Exception:
            pass
        raise ValueError('Cannot decode signature: unknown format')
