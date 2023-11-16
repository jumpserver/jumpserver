from __future__ import unicode_literals

import copy
import os
from importlib import import_module

import jms_storage
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.fields import EncryptJsonDictTextField
from common.db.models import JMSBaseModel
from common.plugins.es import QuerySet as ESQuerySet
from common.utils import get_logger
from common.utils.timezone import local_now_date_display
from terminal import const
from terminal.backends import TYPE_ENGINE_MAPPING
from .terminal import Terminal
from ..session.command import Command

logger = get_logger(__file__)


class CommonStorageModelMixin(models.Model):
    name = models.CharField(max_length=128, verbose_name=_("Name"), unique=True)
    meta = EncryptJsonDictTextField(default={})
    is_default = models.BooleanField(default=False, verbose_name=_('Default storage'))

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def set_to_default(self):
        self.is_default = True
        self.save(update_fields=['is_default'])
        self.__class__.objects.select_for_update() \
            .filter(is_default=True) \
            .exclude(id=self.id) \
            .update(is_default=False)

    @classmethod
    def default(cls):
        objs = cls.objects.filter(is_default=True)
        if not objs:
            objs = cls.objects.filter(name='default', type='server')
        if not objs:
            objs = cls.objects.all()
        return objs.first()


class CommandStorage(CommonStorageModelMixin, JMSBaseModel):
    type = models.CharField(
        max_length=16, choices=const.CommandStorageType.choices,
        default=const.CommandStorageType.server.value, verbose_name=_('Type'),
    )

    @property
    def type_null(self):
        return self.type == const.CommandStorageType.null.value

    @property
    def type_server(self):
        return self.type == const.CommandStorageType.server.value

    @property
    def type_es(self):
        return self.type == const.CommandStorageType.es.value

    @property
    def type_null_or_server(self):
        return self.type_null or self.type_server

    @property
    def config(self):
        config = copy.deepcopy(self.meta)
        config.update({'TYPE': self.type})
        return config

    @property
    def valid_config(self):
        config = self.config
        if self.type_es and config.get('INDEX_BY_DATE'):
            engine_mod = import_module(TYPE_ENGINE_MAPPING[self.type])
            # 这里使用一个全新的 config, 防止修改当前的 config
            store = engine_mod.CommandStore(self.config)
            store._ensure_index_exists()
            index_prefix = config.get('INDEX') or 'jumpserver'
            date = local_now_date_display()
            config['INDEX'] = '%s-%s' % (index_prefix, date)
        return config

    def is_valid(self):
        if self.type_null_or_server:
            return True

        if self.type not in TYPE_ENGINE_MAPPING:
            logger.error(f'Command storage `{self.type}` not support')
            return False

        engine_mod = import_module(TYPE_ENGINE_MAPPING[self.type])
        store = engine_mod.CommandStore(self.config)
        return store.ping(timeout=3)

    def is_use(self):
        return Terminal.objects.filter(command_storage=self.name, is_deleted=False).exists()

    def get_command_queryset(self):
        if self.type_null:
            return Command.objects.none()

        if self.type_server:
            return Command.objects.all()

        if self.type in TYPE_ENGINE_MAPPING:
            engine_mod = import_module(TYPE_ENGINE_MAPPING[self.type])
            store = engine_mod.CommandStore(self.config)
            qs = ESQuerySet(store)
            qs.model = Command
            return qs

        logger.error(f'Command storage `{self.type}` not support')
        return Command.objects.none()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(
            force_insert=force_insert, force_update=force_update,
            using=using, update_fields=update_fields
        )

        if self.type in TYPE_ENGINE_MAPPING:
            engine_mod = import_module(TYPE_ENGINE_MAPPING[self.type])
            backend = engine_mod.CommandStore(self.config)
            backend.pre_use_check()

    class Meta:
        verbose_name = _("Command storage")


class ReplayStorage(CommonStorageModelMixin, JMSBaseModel):
    type = models.CharField(
        max_length=16, choices=const.ReplayStorageType.choices,
        default=const.ReplayStorageType.server.value, verbose_name=_('Type')
    )

    @property
    def type_null(self):
        return self.type == const.ReplayStorageType.null.value

    @property
    def type_server(self):
        return self.type == const.ReplayStorageType.server.value

    @property
    def type_null_or_server(self):
        return self.type_null or self.type_server

    @property
    def type_swift(self):
        return self.type == const.ReplayStorageType.swift.value

    @property
    def type_sftp(self):
        return self.type == const.ReplayStorageType.sftp.value

    @property
    def type_ceph(self):
        return self.type == const.ReplayStorageType.ceph.value

    @property
    def config(self):
        _config = {}

        # add type config
        if self.type_ceph:
            _type = const.ReplayStorageType.s3.value
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
        return Terminal.objects.filter(replay_storage=self.name, is_deleted=False).exists()

    class Meta:
        verbose_name = _("Replay storage")
