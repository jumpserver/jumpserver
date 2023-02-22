# -*- coding: utf-8 -*-
#
import uuid
from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils.common import lazyproperty
from orgs.mixins.models import OrgModelMixin


class AbstractSessionCommand(OrgModelMixin):
    class RiskLevelChoices(models.IntegerChoices):
        ordinary = 0, _('Ordinary')
        dangerous = 5, _('Dangerous')

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=64, db_index=True, verbose_name=_("User"))
    asset = models.CharField(max_length=128, db_index=True, verbose_name=_("Asset"))
    account = models.CharField(max_length=64, db_index=True, verbose_name=_("Account"))
    input = models.CharField(max_length=128, db_index=True, verbose_name=_("Input"))
    output = models.CharField(max_length=1024, blank=True, verbose_name=_("Output"))
    session = models.CharField(max_length=36, db_index=True, verbose_name=_("Session"))
    risk_level = models.SmallIntegerField(
        default=RiskLevelChoices.ordinary, choices=RiskLevelChoices.choices, db_index=True,
        verbose_name=_("Risk level")
    )
    timestamp = models.IntegerField(db_index=True)

    class Meta:
        abstract = True

    @lazyproperty
    def timestamp_display(self):
        return datetime.fromtimestamp(self.timestamp)

    @lazyproperty
    def remote_addr(self):
        from terminal.models import Session
        session = Session.objects.filter(id=self.session).first()
        if session:
            return session.remote_addr
        else:
            return ''

    @classmethod
    def get_risk_level_str(cls, risk_level):
        risk_mapper = dict(cls.RiskLevelChoices.choices)
        return risk_mapper.get(risk_level)

    def to_dict(self):
        d = {}
        for field in self._meta.fields:
            d[field.name] = getattr(self, field.name)
        return d

    def __str__(self):
        return self.input
