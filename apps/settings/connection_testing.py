from django.conf import settings
from rest_framework.exceptions import ValidationError

from common.serializers.fields import EncryptedField


def get_test_config(serializer_class, data, required_secrets=()):
    """Validate a request-local configuration without changing saved settings."""
    fields = serializer_class().fields
    values = dict(data)
    secret_fields = []
    for name, field in fields.items():
        if field.read_only:
            continue
        if isinstance(field, EncryptedField):
            secret_fields.append(name)
            # Saved secrets are already decrypted; never pass them through the
            # session-cipher decoder again.
            if values.get(name) in ('', None):
                values.pop(name, None)
        elif name not in values and hasattr(settings, name):
            values[name] = getattr(settings, name)

    serializer = serializer_class(data=values)
    serializer.is_valid(raise_exception=True)
    config = dict(serializer.validated_data)
    for name in secret_fields:
        if not config.get(name):
            config[name] = getattr(settings, name, '') or ''
    errors = {
        name: fields[name].error_messages['blank']
        for name in required_secrets if not config.get(name)
    }
    if errors:
        raise ValidationError(errors)
    return config


def verify_im_credentials(request_class, **kwargs):
    """Verify credentials with a fresh token request, without production caches."""
    class ConnectionTestRequest(request_class):
        def init_access_token(self):
            self.access_token, _ = self.request_access_token()

    return ConnectionTestRequest(timeout=30, **kwargs)
