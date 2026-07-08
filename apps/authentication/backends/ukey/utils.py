# -*- coding: utf-8 -*-
#
import base64

# SM2 曲线 OID：1.2.156.10197.1.301
# DER 编码：06 08 2a 81 1c cf 55 01 82 2d
SM2_OID_DER = bytes([0x06, 0x08, 0x2a, 0x81, 0x1c, 0xcf, 0x55, 0x01, 0x82, 0x2d])


def is_sm2_pem(pem_content):
    """
    通过查找 SM2 曲线 OID 字节序列判断 PEM 数据（证书 / CSR / 公钥等）是否使用 SM2 算法。

    pem_content: 标准 PEM 字符串（含 -----BEGIN ... ----- 头尾）。
    返回 True 表示包含 SM2 OID，否则返回 False。
    """
    pem_lines = pem_content.strip().splitlines()
    b64 = ''.join(ln for ln in pem_lines if not ln.startswith('-----'))
    try:
        der = base64.b64decode(b64)
    except Exception:
        return False
    return SM2_OID_DER in der


def detect_cert_algorithm(pem_content):
    """
    从 PEM 内容检测公钥算法，返回 'SM2' / 'RSA-1024' / 'RSA-2048' / 'ECDSA-256' 等字符串，
    无法识别时返回空字符串。支持证书、CSR、公钥等任意 PEM 格式。
    """
    if not pem_content:
        return ''

    try:
        if is_sm2_pem(pem_content):
            return 'SM2'
        from cryptography import x509
        from cryptography.hazmat.primitives.asymmetric import ec, rsa
        cert = x509.load_pem_x509_certificate(pem_content.encode())
        pub = cert.public_key()
        if isinstance(pub, rsa.RSAPublicKey):
            return 'RSA-{}'.format(pub.key_size)
        if isinstance(pub, ec.EllipticCurvePublicKey):
            return 'ECDSA-{}'.format(pub.key_size)
        return ''
    except Exception:
        return ''
