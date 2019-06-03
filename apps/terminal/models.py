from __future__ import unicode_literals

import os
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.cache import cache

from users.models import User
from orgs.mixins import OrgModelMixin
from common.utils import get_command_storage_setting, get_replay_storage_setting
from .backends import get_multi_command_storage
from .backends.command.models import AbstractSessionCommand


class Terminal(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=32, verbose_name=_('Name'))
    remote_addr = models.CharField(max_length=128, blank=True, verbose_name=_('Remote Address'))
    ssh_port = models.IntegerField(verbose_name=_('SSH Port'), default=2222)
    http_port = models.IntegerField(verbose_name=_('HTTP Port'), default=5000)
    command_storage = models.CharField(max_length=128, verbose_name=_("Command storage"), default='default')
    replay_storage = models.CharField(max_length=128, verbose_name=_("Replay storage"), default='default')
    user = models.OneToOneField(User, related_name='terminal', verbose_name='Application User', null=True, on_delete=models.CASCADE)
    is_accepted = models.BooleanField(default=False, verbose_name='Is Accepted')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    STATUS_KEY_PREFIX = 'terminal_status_'

    @property
    def is_alive(self):
        key = self.STATUS_KEY_PREFIX + str(self.id)
        return bool(cache.get(key))

    @is_alive.setter
    def is_alive(self, value):
        key = self.STATUS_KEY_PREFIX + str(self.id)
        cache.set(key, value, 60)

    @property
    def is_active(self):
        if self.user and self.user.is_active:
            return True
        return False

    @is_active.setter
    def is_active(self, active):
        if self.user:
            self.user.is_active = active
            self.user.save()

    def get_command_storage_setting(self):
        storage_all = get_command_storage_setting()
        if self.command_storage in storage_all:
            storage = storage_all.get(self.command_storage)
        else:
            storage = storage_all.get('default')
        return {"TERMINAL_COMMAND_STORAGE": storage}

    def get_replay_storage_setting(self):
        storage_all = get_replay_storage_setting()
        if self.replay_storage in storage_all:
            storage = storage_all.get(self.replay_storage)
        else:
            storage = storage_all.get('default')
        return {"TERMINAL_REPLAY_STORAGE": storage}

    @property
    def config(self):
        configs = {}
        for k in dir(settings):
            if not k.startswith('TERMINAL'):
                continue
            configs[k] = getattr(settings, k)
        configs.update(self.get_command_storage_setting())
        configs.update(self.get_replay_storage_setting())
        configs.update({
            'SECURITY_MAX_IDLE_TIME': settings.SECURITY_MAX_IDLE_TIME
        })
        return configs

    @property
    def service_account(self):
        return self.user

    def create_app_user(self):
        random = uuid.uuid4().hex[:6]
        user, access_key = User.create_app_user(
            name="{}-{}".format(self.name, random), comment=self.comment
        )
        self.user = user
        self.save()
        return user, access_key

    def delete(self, using=None, keep_parents=False):
        if self.user:
            self.user.delete()
        self.user = None
        self.is_deleted = True
        self.save()
        return

    def __str__(self):
        status = "Active"
        if not self.is_accepted:
            status = "NotAccept"
        elif self.is_deleted:
            status = "Deleted"
        elif not self.is_active:
            status = "Disable"
        return '%s: %s' % (self.name, status)

    class Meta:
        ordering = ('is_accepted',)
        db_table = "terminal"


class Status(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    session_online = models.IntegerField(verbose_name=_("Session Online"), default=0)
    cpu_used = models.FloatField(verbose_name=_("CPU Usage"))
    memory_used = models.FloatField(verbose_name=_("Memory Used"))
    connections = models.IntegerField(verbose_name=_("Connections"))
    threads = models.IntegerField(verbose_name=_("Threads"))
    boot_time = models.FloatField(verbose_name=_("Boot Time"))
    terminal = models.ForeignKey(Terminal, null=True, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'terminal_status'
        get_latest_by = 'date_created'

    def __str__(self):
        return self.date_created.strftime("%Y-%m-%d %H:%M:%S")


class Session(OrgModelMixin):
    LOGIN_FROM_CHOICES = (
        ('ST', 'SSH Terminal'),
        ('WT', 'Web Terminal'),
    )
    PROTOCOL_CHOICES = (
        ('ssh', 'ssh'),
        ('rdp', 'rdp'),
        ('vnc', 'vnc')
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_("User"))
    asset = models.CharField(max_length=1024, verbose_name=_("Asset"))
    system_user = models.CharField(max_length=128, verbose_name=_("System user"))
    login_from = models.CharField(max_length=2, choices=LOGIN_FROM_CHOICES, default="ST")
    remote_addr = models.CharField(max_length=15, verbose_name=_("Remote addr"), blank=True, null=True)
    is_finished = models.BooleanField(default=False)
    has_replay = models.BooleanField(default=False, verbose_name=_("Replay"))
    has_command = models.BooleanField(default=False, verbose_name=_("Command"))
    terminal = models.ForeignKey(Terminal, null=True, on_delete=models.SET_NULL)
    protocol = models.CharField(choices=PROTOCOL_CHOICES, default='ssh', max_length=8)
    date_last_active = models.DateTimeField(verbose_name=_("Date last active"), default=timezone.now)
    date_start = models.DateTimeField(verbose_name=_("Date start"), db_index=True, default=timezone.now)
    date_end = models.DateTimeField(verbose_name=_("Date end"), null=True)

    upload_to = 'replay'
    ACTIVE_CACHE_KEY_PREFIX = 'SESSION_ACTIVE_{}'
    _DATE_START_FIRST_HAS_REPLAY_RDP_SESSION = None

    def get_rel_replay_path(self, version=2):
        """
        获取session日志的文件路径
        :param version: 原来后缀是 .gz，为了统一新版本改为 .replay.gz
        :return:
        """
        suffix = '.replay.gz'
        if version == 1:
            suffix = '.gz'
        date = self.date_start.strftime('%Y-%m-%d')
        return os.path.join(date, str(self.id) + suffix)

    def get_local_path(self, version=2):
        rel_path = self.get_rel_replay_path(version=version)
        if version == 2:
            local_path = os.path.join(self.upload_to, rel_path)
        else:
            local_path = rel_path
        return local_path

    @property
    def _date_start_first_has_replay_rdp_session(self):
        if self._DATE_START_FIRST_HAS_REPLAY_RDP_SESSION is None:
            instance = self.__class__.objects.filter(
                protocol='rdp', has_replay=True).order_by('date_start').first()
            if not instance:
                return None
            self._DATE_START_FIRST_HAS_REPLAY_RDP_SESSION = instance.date_start

        return self._DATE_START_FIRST_HAS_REPLAY_RDP_SESSION

    def can_replay(self):
        if self.has_replay:
            return True

        # 判断对RDP Session添加上报has_replay状态机制之前的录像回放
        if self._date_start_first_has_replay_rdp_session is None:
            return True

        if self.date_start < self._date_start_first_has_replay_rdp_session:
            return True

        return False

    def save_to_storage(self, f):
        local_path = self.get_local_path()
        try:
            name = default_storage.save(local_path, f)
            return name, None
        except OSError as e:
            return None, e

    @classmethod
    def set_sessions_active(cls, sessions_id):
        data = {cls.ACTIVE_CACHE_KEY_PREFIX.format(i): i for i in sessions_id}
        cache.set_many(data, timeout=5*60)

    @classmethod
    def get_active_sessions(cls):
        return cls.objects.filter(is_finished=False)

    def is_active(self):
        if self.protocol in ['ssh', 'telnet']:
            key = self.ACTIVE_CACHE_KEY_PREFIX.format(self.id)
            return bool(cache.get(key))
        return True

    @property
    def command_amount(self):
        command_store = get_multi_command_storage()
        return command_store.count(session=str(self.id))

    class Meta:
        db_table = "terminal_session"
        ordering = ["-date_start"]

    def __str__(self):
        return "{0.id} of {0.user} to {0.asset}".format(self)


class Task(models.Model):
    NAME_CHOICES = (
        ("kill_session", "Kill Session"),
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, choices=NAME_CHOICES, verbose_name=_("Name"))
    args = models.CharField(max_length=1024, verbose_name=_("Args"))
    terminal = models.ForeignKey(Terminal, null=True, on_delete=models.SET_NULL)
    is_finished = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_finished = models.DateTimeField(null=True)

    class Meta:
        db_table = "terminal_task"


class Command(AbstractSessionCommand):

    class Meta:
        db_table = "terminal_command"
        ordering = ('-timestamp',)
