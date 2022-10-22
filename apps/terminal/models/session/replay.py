from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin
from .session import Session


class SessionReplay(CommonModelMixin):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, verbose_name=_("Session"))

    class Meta:
        verbose_name = _("Session replay")
        permissions = [
            ('upload_sessionreplay', _("Can upload session replay")),
            ('download_sessionreplay', _("Can download session replay")),
        ]


