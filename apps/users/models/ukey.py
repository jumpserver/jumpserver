from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db import fields
from common.db.models import JMSBaseModel

__all__ = ["UKey"]


class UKey(JMSBaseModel):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="user_usb_key",
        verbose_name=_("User"),
    )
    u_key_serial = models.CharField(
        max_length=128, unique=True, verbose_name=_("USB Key Serial")
    )
    # 保存的是公钥的x+y值，16进制的32位
    u_key_public_key = fields.EncryptTextField(verbose_name=_("USB Key Public Key"))

    class Meta:
        verbose_name = _("User UKey")
