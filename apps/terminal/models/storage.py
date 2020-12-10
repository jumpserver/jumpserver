from __future__ import unicode_literals

import os
import jms_storage

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from common.mixins import CommonModelMixin
from common.fields.model import EncryptJsonDictTextField
from .. import const
from .terminal import Terminal


class CommandStorage(CommonModelMixin):
    TYPE_CHOICES = const.COMMAND_STORAGE_TYPE_CHOICES
    TYPE_DEFAULTS = dict(const.REPLAY_STORAGE_TYPE_CHOICES_DEFAULT).keys()
    TYPE_SERVER = const.COMMAND_STORAGE_TYPE_SERVER

    name = models.CharField(max_length=128, verbose_name=_("Name"), unique=True)
    type = models.CharField(
        max_length=16, choices=TYPE_CHOICES, verbose_name=_('Type'),
        default=TYPE_SERVER
    )
    meta = EncryptJsonDictTextField(default={})
    comment = models.TextField(
        max_length=128, default='', blank=True, verbose_name=_('Comment')
    )

    def __str__(self):
        return self.name

    @property
    def config(self):
        config = self.meta
        config.update({'TYPE': self.type})
        return config

    def in_defaults(self):
        return self.type in self.TYPE_DEFAULTS

    def is_valid(self):
        if self.in_defaults():
            return True
        storage = jms_storage.get_log_storage(self.config)
        return storage.ping()

    def is_using(self):
        return Terminal.objects.filter(command_storage=self.name).exists()


class ReplayStorage(CommonModelMixin):
    TYPE_CHOICES = const.REPLAY_STORAGE_TYPE_CHOICES
    TYPE_SERVER = const.REPLAY_STORAGE_TYPE_SERVER
    TYPE_DEFAULTS = dict(const.REPLAY_STORAGE_TYPE_CHOICES_DEFAULT).keys()

    name = models.CharField(max_length=128, verbose_name=_("Name"), unique=True)
    type = models.CharField(
        max_length=16, choices=TYPE_CHOICES, verbose_name=_('Type'),
        default=TYPE_SERVER
    )
    meta = EncryptJsonDictTextField(default={})
    comment = models.TextField(
        max_length=128, default='', blank=True, verbose_name=_('Comment')
    )

    def __str__(self):
        return self.name

    def convert_type(self):
        s3_type_list = [const.REPLAY_STORAGE_TYPE_CEPH]
        tp = self.type
        if tp in s3_type_list:
            tp = const.REPLAY_STORAGE_TYPE_S3
        return tp

    def get_extra_config(self):
        extra_config = {'TYPE': self.convert_type()}
        if self.type == const.REPLAY_STORAGE_TYPE_SWIFT:
            extra_config.update({'signer': 'S3SignerType'})
        return extra_config

    @property
    def config(self):
        config = self.meta
        extra_config = self.get_extra_config()
        config.update(extra_config)
        return config

    def in_defaults(self):
        return self.type in self.TYPE_DEFAULTS

    def is_valid(self):
        if self.in_defaults():
            return True
        storage = jms_storage.get_object_storage(self.config)
        target = 'tests.py'
        src = os.path.join(settings.BASE_DIR, 'common', target)
        return storage.is_valid(src, target)

    def is_using(self):
        return Terminal.objects.filter(replay_storage=self.name).exists()
