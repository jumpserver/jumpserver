# -*- coding: utf-8 -*-
#

from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _

# Replay & Command Storage Choices
# --------------------------------


class ReplayStorageTypeChoices(TextChoices):
    null = 'null', 'Null',
    server = 'server', 'Server'
    s3 = 's3', 'S3'
    ceph = 'ceph', 'Ceph'
    swift = 'swift', 'Swift'
    oss = 'oss', 'OSS'
    azure = 'azure', 'Azure'


class CommandStorageTypeChoices(TextChoices):
    null = 'null', 'Null',
    server = 'server', 'Server'
    es = 'es', 'Elasticsearch'


# Component Status Choices
# ------------------------

class ComponentStatusChoices(TextChoices):
    critical = 'critical', _('Critical')
    high = 'high', _('High')
    normal = 'normal', _('Normal')

    @classmethod
    def status(cls):
        return set(dict(cls.choices).keys())


class TerminalTypeChoices(TextChoices):
    koko = 'koko', 'KoKo'
    guacamole = 'guacamole', 'Guacamole'
    omnidb = 'omnidb', 'OmniDB'
    xrdp = 'xrdp', 'xrdp'

    @classmethod
    def types(cls):
        return set(dict(cls.choices).keys())

