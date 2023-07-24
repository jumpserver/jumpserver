import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import BaseCreateUpdateModel, CASCADE_SIGNAL_SKIP


class SSOToken(BaseCreateUpdateModel):
    """
    类似腾讯企业邮的 [单点登录](https://exmail.qq.com/qy_mng_logic/doc#10036)
    出于安全考虑，这里的 `token` 使用一次随即过期。但我们保留每一个生成过的 `token`。
    """
    authkey = models.UUIDField(primary_key=True, default=uuid.uuid4, verbose_name=_('Token'))
    expired = models.BooleanField(default=False, verbose_name=_('Expired'))
    user = models.ForeignKey('users.User', on_delete=CASCADE_SIGNAL_SKIP, verbose_name=_('User'),
                             db_constraint=False)

    class Meta:
        verbose_name = _('SSO token')
