from __future__ import unicode_literals

import os
from importlib import import_module

import jms_storage
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from common.mixins import CommonModelMixin
from common.utils import get_logger
from common.fields.model import EncryptJsonDictTextField
from terminal.backends import TYPE_ENGINE_MAPPING
from .terminal import Terminal
from .command import Command
from .. import const


logger = get_logger(__file__)


class CommandStorage(CommonModelMixin):
    name = models.CharField(max_length=128, verbose_name=_("Name"), unique=True)
    type = models.CharField(
        max_length=16, choices=const.CommandStorageTypeChoices.choices,
        default=const.CommandStorageTypeChoices.server.value, verbose_name=_('Type'),
    )
    meta = EncryptJsonDictTextField(default={})
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name

    @property
    def type_null(self):
        return self.type == const.CommandStorageTypeChoices.null.value

    @property
    def type_server(self):
        return self.type == const.CommandStorageTypeChoices.server.value

    @property
    def type_null_or_server(self):
        return self.type_null or self.type_server

    @property
    def config(self):
        config = self.meta
        config.update({'TYPE': self.type})
        return config

    def is_valid(self):
        if self.type_null_or_server:
            return True
        storage = jms_storage.get_log_storage(self.config)
        return storage.ping()

    def is_use(self):
        return Terminal.objects.filter(command_storage=self.name).exists()

    def get_command_queryset(self):
        if self.type_server:
            qs = Command.objects.all()
        else:
            if self.type not in TYPE_ENGINE_MAPPING:
                logger.error(f'Command storage `{self.type}` not support')
                return Command.objects.none()
            engine_mod = import_module(TYPE_ENGINE_MAPPING[self.type])
            qs = engine_mod.QuerySet(self.config)
            qs.model = Command
        return qs


class ReplayStorage(CommonModelMixin):
    name = models.CharField(max_length=128, verbose_name=_("Name"), unique=True)
    type = models.CharField(
        max_length=16, choices=const.ReplayStorageTypeChoices.choices,
        default=const.ReplayStorageTypeChoices.server.value, verbose_name=_('Type')
    )
    meta = EncryptJsonDictTextField(default={})
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name

    @property
    def type_null(self):
        return self.type == const.ReplayStorageTypeChoices.null.value

    @property
    def type_server(self):
        return self.type == const.ReplayStorageTypeChoices.server.value

    @property
    def type_null_or_server(self):
        return self.type_null or self.type_server

    @property
    def type_swift(self):
        return self.type == const.ReplayStorageTypeChoices.swift.value

    @property
    def type_ceph(self):
        return self.type == const.ReplayStorageTypeChoices.ceph.value

    @property
    def config(self):
        _config = {}

        # add type config
        if self.type_ceph:
            _type = const.ReplayStorageTypeChoices.s3.value
        else:
            _type = self.type
        _config.update({'TYPE': _type})

        # add special config
        if self.type_swift:
            _config.update({'signer': 'S3SignerType'})

        # add meta config
        _config.update(self.meta)
        return _config

    def is_valid(self):
        if self.type_null_or_server:
            return True
        storage = jms_storage.get_object_storage(self.config)
        target = 'tests.py'
        src = os.path.join(settings.BASE_DIR, 'common', target)
        return storage.is_valid(src, target)

    def is_use(self):
        return Terminal.objects.filter(replay_storage=self.name).exists()
