from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel
from .session import Session


class SessionReplay(JMSBaseModel):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, verbose_name=_("Session"))

    class Meta:
        verbose_name = _("Session replay")
        permissions = [
            ('upload_sessionreplay', _("Can upload session replay")),
            ('download_sessionreplay', _("Can download session replay")),
        ]
