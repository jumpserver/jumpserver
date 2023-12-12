# -*- coding: utf-8 -*-
#

from django.db.models import TextChoices, IntegerChoices
from django.utils.translation import gettext_lazy as _


class RiskLevelChoices(IntegerChoices):
    accept = 0, _('Accept')
    warning = 4, _('Warning')
    reject = 5, _('Reject')
    review_reject = 6, _('Review & Reject')
    review_accept = 7, _('Review & Accept')
    review_cancel = 8, _('Review & Cancel')

    @classmethod
    def get_label(cls, level):
        label = dict(cls.choices).get(level)
        return label


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
    sftp = 'sftp', 'SFTP'


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
    panda = 'panda', 'Panda'

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
    readonly = "readonly", _('Read only')
    writable = "writable", _('Writable')


class TaskNameType(TextChoices):
    kill_session = "kill_session", _('Kill session')
    lock_session = "lock_session", _('Lock session')
    unlock_session = "unlock_session", _('Unlock session')


class SessionErrorReason(TextChoices):
    connect_failed = 'connect_failed', _('Connect failed')
    replay_create_failed = 'replay_create_failed', _('Replay create failed')
    replay_upload_failed = 'replay_upload_failed', _('Replay upload failed')
    replay_convert_failed = 'replay_convert_failed', _('Replay convert failed')
    replay_unsupported = 'replay_unsupported', _('Replay unsupported')
