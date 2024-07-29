import sshpubkeys

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel, CASCADE_SIGNAL_SKIP
from users.models import AuthMixin
from common.db import fields


class SSHKey(JMSBaseModel, AuthMixin):
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    private_key = fields.EncryptTextField(
        blank=True, null=True, verbose_name=_("Private key")
    )
    public_key = fields.EncryptTextField(
        blank=True, null=True, verbose_name=_("Public key")
    )
    date_last_used = models.DateTimeField(null=True, blank=True, verbose_name=_('Date last used'))
    user = models.ForeignKey(
        'users.User', on_delete=CASCADE_SIGNAL_SKIP, verbose_name=_('User'), db_constraint=False,
        related_name='ssh_keys'
    )

    class Meta:
        verbose_name = _('SSH key')
