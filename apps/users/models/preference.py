from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.utils import Encryptor
from common.utils import get_logger

logger = get_logger(__name__)


class Preference(models.Model):
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    category = models.CharField(max_length=128, verbose_name=_('Category'))
    value = models.TextField(verbose_name=_("Value"), null=True, blank=True)
    encrypted = models.BooleanField(default=False, verbose_name=_('Encrypted'))
    user = models.ForeignKey(
        'users.User', verbose_name=_("Users"), related_name='preferences', on_delete=models.CASCADE
    )

    def __str__(self):
        return f'{self.name}({self.user.username})'

    @classmethod
    def encrypt(cls, value):
        return Encryptor(value).encrypt()

    @classmethod
    def decrypt(cls, value):
        return Encryptor(value).decrypt()

    @property
    def decrypt_value(self):
        if self.encrypted:
            return self.decrypt(self.value)
        return self.value

    class Meta:
        db_table = "users_preference"
        verbose_name = _("Preference")
        unique_together = [('name', 'user_id')]
