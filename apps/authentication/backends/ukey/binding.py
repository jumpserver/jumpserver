from users.models import UKeyCertificateBinding
from .exceptions import UKeyAuthError
from .providers import get_provider


def verify_identity(snapshot, code, cert_value, signature_value):
    provider = get_provider(snapshot)
    if provider.binding_mode != 'certificate':
        raise UKeyAuthError('Certificate binding is not supported by this CA provider')
    claims = provider.verify_proof(cert_value, signature_value, code)
    # Provider IDs and database lookup fields are owned by the core, not proof input.
    return {name: claims[name] for name in (
        'issuer_fingerprint', 'serial_number', 'certificate_fingerprint',
    )} | {'provider': provider.id}


def binding_version(user_id, provider):
    value = UKeyCertificateBinding.objects.filter(user_id=user_id, provider=provider).values_list('version', flat=True).first()
    return str(value) if value else ''


def record_change(user, action, provider):
    from audits.handler import create_or_update_operate_log
    create_or_update_operate_log(
        'update', 'UKey certificate binding', resource=user,
        after={'provider': provider, 'binding_action': action}, object_name='User',
    )
