from django.db.models import TextChoices

RSA_PRIVATE_KEY = 'rsa_private_key'
RSA_PUBLIC_KEY = 'rsa_public_key'


class ConfirmType(TextChoices):
    RELOGIN = 'relogin', 'Re-Login'
    PASSWORD = 'password', 'Password'
    MFA = 'mfa', 'MFA'
