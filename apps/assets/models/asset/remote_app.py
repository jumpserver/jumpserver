from django.utils.translation import gettext_lazy as _
from django.db import models

from orgs.mixins.models import OrgModelMixin
from common.mixins.models import CommonModelMixin
from .common import Asset


class RemoteAppHost(CommonModelMixin, OrgModelMixin):
    host = models.ForeignKey('assets.Host', verbose_name=_("Host"))
    system_user = models.ForeignKey('assets.SystemUser', verbose_name=_("System user"))


class RemoteApp(Asset):
    app_path = models.CharField(max_length=1024, verbose_name=_("App path"))
    attrs = models.JSONField(default=dict, verbose_name=_('Attrs'))
