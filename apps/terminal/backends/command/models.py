# -*- coding: utf-8 -*-
#
import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgModelMixin


class AbstractSessionCommand(OrgModelMixin):
    RISK_LEVEL_ORDINARY = 0
    RISK_LEVEL_DANGEROUS = 5
    RISK_LEVEL_CHOICES = (
        (RISK_LEVEL_ORDINARY, _('Ordinary')),
        (RISK_LEVEL_DANGEROUS, _('Dangerous')),
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=64, db_index=True, verbose_name=_("User"))
    asset = models.CharField(max_length=128, db_index=True, verbose_name=_("Asset"))
    system_user = models.CharField(max_length=64, db_index=True, verbose_name=_("System user"))
    input = models.CharField(max_length=128, db_index=True, verbose_name=_("Input"))
    output = models.CharField(max_length=1024, blank=True, verbose_name=_("Output"))
    session = models.CharField(max_length=36, db_index=True, verbose_name=_("Session"))
    risk_level = models.SmallIntegerField(default=RISK_LEVEL_ORDINARY, choices=RISK_LEVEL_CHOICES, db_index=True, verbose_name=_("Risk level"))
    timestamp = models.IntegerField(db_index=True)

    class Meta:
        abstract = True

    @classmethod
    def from_dict(cls, d):
        self = cls()
        for k, v in d.items():
            setattr(self, k, v)
        return self

    @classmethod
    def from_multi_dict(cls, l):
        commands = []
        for d in l:
            command = cls.from_dict(d)
            commands.append(command)
        return commands

    def to_dict(self):
        d = {}
        for field in self._meta.fields:
            d[field.name] = getattr(self, field.name)
        return d

    def __str__(self):
        return self.input
