# -*- coding: utf-8 -*-
#

from django.db.models import TextChoices, IntegerChoices
from django.utils.translation import ugettext_lazy as _


class RiskLevelChoices(IntegerChoices):
    accept = 0, _('Accept')
    warning = 4, _('Warning')
    reject = 5, _('Reject')
    review_reject = 6, _('Review & Reject')
    review_accept = 7, _('Review & Accept')
    review_cancel = 8, _('Review & Cancel')

    @classmethod
    def get_risk_level_str(cls, risk_level):
        risk_mapper = dict(cls.choices)
        return risk_mapper.get(risk_level)


class ReplayStorageType(TextChoices):
    null = 'null', 'Null',
    server = 'server', 'Server'
    s3 = 's3', 'S3'
    ceph = 'ceph', 'Ceph'
    swift = 'swift', 'Swift'
    oss = 'oss', 'OSS'
    azure = 'azure', 'Azure'
    obs = 'obs', 'OBS'
    cos = 'cos', 'COS'


class CommandStorageType(TextChoices):
    null = 'null', 'Null',
    server = 'server', 'Server'
    es = 'es', 'Elasticsearch'


# Component Status Choices
# ------------------------

class ComponentLoad(TextChoices):
    critical = 'critical', _('Critical')
    high = 'high', _('High')
    normal = 'normal', _('Normal')
    offline = 'offline', _('Offline')

    @classmethod
    def status(cls):
        return set(dict(cls.choices).keys())


class TerminalType(TextChoices):
    koko = 'koko', 'KoKo'
    guacamole = 'guacamole', 'Guacamole'
    omnidb = 'omnidb', 'OmniDB'
    xrdp = 'xrdp', 'Xrdp'
    lion = 'lion', 'Lion'
    core = 'core', 'Core'
    celery = 'celery', 'Celery'
    magnus = 'magnus', 'Magnus'
    razor = 'razor', 'Razor'
    tinker = 'tinker', 'Tinker'
    video_worker = 'video_worker', 'Video Worker'
    chen = 'chen', 'Chen'
    kael = 'kael', 'Kael'

    @classmethod
    def types(cls):
        return set(dict(cls.choices).keys())


class PublishStatus(TextChoices):
    pending = 'pending', _('Pending')
    success = 'success', _("Success")
    failed = 'failed', _("Failed")
    mismatch = 'mismatch', _("Mismatch")


class SessionType(TextChoices):
    normal = 'normal', _('Normal')
    tunnel = 'tunnel', _('Tunnel')
    command = 'command', _('Command')
    sftp = 'sftp', _('SFTP')


class ActionPermission(TextChoices):
    readonly = "readonly", _('Read Only')
    writable = "writable", _('Writable')
