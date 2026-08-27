from django.db import models
from django.utils.translation import gettext_lazy as _


class CredentialPolicyMode(models.TextChoices):
    static = 'static', _('Rotating account')
    dynamic = 'dynamic', _('Temporary account')


class CredentialPolicyStatus(models.TextChoices):
    enabled = 'enabled', _('Enabled')
    rotating = 'rotating', _('Rotating')
    disabling = 'disabling', _('Disabling')
    disabled = 'disabled', _('Disabled')
    uncertain = 'uncertain', _('Uncertain')


class CredentialIssueStatus(models.TextChoices):
    pending = 'pending', _('Pending')
    running = 'running', _('Running')
    cleaning = 'cleaning', _('Cleaning')
    succeeded = 'succeeded', _('Succeeded')
    failed = 'failed', _('Failed')
    timed_out = 'timed_out', _('Timed out')


class CredentialLeaseStatus(models.TextChoices):
    active = 'active', _('Active')
    revoking = 'revoking', _('Revoking')
    revoked = 'revoked', _('Revoked')
    expired = 'expired', _('Expired')
