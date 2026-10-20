from django.db import models
from django.utils.translation import gettext_lazy as _


class AccountProvisioning(models.Model):
    """Keep failed/queued first-login accounts distinct from existing accounts."""

    account = models.OneToOneField(
        'accounts.Account', primary_key=True, on_delete=models.CASCADE,
        related_name='provisioning',
    )
    user = models.ForeignKey('users.User', null=True, on_delete=models.SET_NULL)
    execution = models.ForeignKey(
        'accounts.AutomationExecution', null=True, on_delete=models.SET_NULL,
    )
    protocol = models.CharField(max_length=16)
    status = models.CharField(max_length=16, default='queued')
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('First-login account provisioning')
        default_permissions = ()
