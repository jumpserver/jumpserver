import fcntl
import os
import stat
import tempfile
from contextlib import contextmanager

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID
from django.conf import settings
from django.utils import timezone


RDP_SIGN_SETTING_NAMES = (
    'RDP_SIGN_ENABLED',
)
RDP_SIGN_UPLOAD_NAMES = ('RDP_SIGN_CERT_CONTENT', 'RDP_SIGN_KEY_CONTENT')
RDP_SIGN_FILENAMES = ('rdp_signer.crt', 'rdp_signer.key')
MAX_PEM_SIZE = 65536


class RDPSigningMaterialError(ValueError):
    def __init__(self, stage):
        self.stage = stage
        super().__init__('Invalid RDP signing material')


def get_rdp_signing_config():
    snapshot = getattr(settings, 'RDP_SIGNING_CONFIG', None)
    if snapshot is not None:
        return snapshot.copy()
    return {name: getattr(settings, name) for name in RDP_SIGN_SETTING_NAMES}


def validate_rdp_signing_material(certificate_pem, private_key_pem):
    stage = 'load_certificate'
    try:
        certificate = x509.load_pem_x509_certificate(certificate_pem)
        stage = 'load_private_key'
        private_key = serialization.load_pem_private_key(private_key_pem, password=None)
        stage = 'validate_certificate_dates'
        if not certificate.not_valid_before_utc <= timezone.now() <= certificate.not_valid_after_utc:
            raise ValueError('Certificate is not currently valid')
        stage = 'validate_certificate_usage'
        usage = certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        if ExtendedKeyUsageOID.CODE_SIGNING not in usage:
            raise ValueError('Certificate does not allow code signing')
        stage = 'validate_private_key'
        if not isinstance(private_key, (rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey)):
            raise ValueError('Unsupported signing key type')
        certificate_public_key = certificate.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        private_public_key = private_key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        if certificate_public_key != private_public_key:
            raise ValueError('Certificate and private key do not match')
        return certificate, private_key
    except Exception:
        raise RDPSigningMaterialError(stage) from None


def read_signing_file(path):
    with open(path, 'rb', opener=lambda name, flags: os.open(name, flags | os.O_NOFOLLOW)) as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError('Signing material must be a regular file')
        content = source.read(MAX_PEM_SIZE + 1)
        if len(content) > MAX_PEM_SIZE:
            raise ValueError('Signing material is too large')
        return content


def load_rdp_signing_material():
    cert_dir = os.path.join(settings.PROJECT_DIR, 'data', 'certs')
    try:
        certificate_pem, private_key_pem = [
            read_signing_file(os.path.join(cert_dir, name)) for name in RDP_SIGN_FILENAMES
        ]
    except Exception:
        raise RDPSigningMaterialError('read_signing_files') from None
    return validate_rdp_signing_material(certificate_pem, private_key_pem)


def write_signing_file(directory, filename, content):
    descriptor, temporary = tempfile.mkstemp(prefix='.rdp-sign-', dir=directory)
    try:
        with os.fdopen(descriptor, 'wb') as destination:
            os.fchmod(destination.fileno(), 0o600)
            destination.write(content)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, os.path.join(directory, filename))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def replace_rdp_signing_files(uploads):
    certificate_pem = uploads[RDP_SIGN_UPLOAD_NAMES[0]].encode('utf-8')
    private_key_pem = uploads[RDP_SIGN_UPLOAD_NAMES[1]].encode('utf-8')
    validate_rdp_signing_material(certificate_pem, private_key_pem)
    directory = os.path.join(settings.PROJECT_DIR, 'data', 'certs')
    os.makedirs(directory, mode=0o700, exist_ok=True)
    if os.path.islink(directory):
        raise RDPSigningMaterialError('unsafe_certificate_directory')
    descriptor = os.open(os.path.join(directory, '.rdp-sign.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'rb') as lock_file:
        if not stat.S_ISREG(os.fstat(lock_file.fileno()).st_mode):
            raise RDPSigningMaterialError('unsafe_lock_file')
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        previous = {}
        for filename in RDP_SIGN_FILENAMES:
            path = os.path.join(directory, filename)
            previous[filename] = read_signing_file(path) if os.path.lexists(path) else None
        try:
            for filename, content in zip(RDP_SIGN_FILENAMES, (certificate_pem, private_key_pem)):
                write_signing_file(directory, filename, content)
            directory_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            yield
        except Exception:
            for filename, content in previous.items():
                if content is None:
                    path = os.path.join(directory, filename)
                    if os.path.lexists(path):
                        os.unlink(path)
                else:
                    write_signing_file(directory, filename, content)
            raise
