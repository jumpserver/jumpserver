import uuid

from django.db import models
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from common.utils import get_logger
from users.models import User
from orgs.utils import tmp_to_root_org
from .status import Status
from .. import const
from ..const import ComponentStatusChoices as StatusChoice
from .session import Session


logger = get_logger(__file__)


class TerminalStatusMixin:
    ALIVE_KEY = 'TERMINAL_ALIVE_{}'
    id: str

    @property
    def latest_status(self):
        return Status.get_terminal_latest_status(self)

    @property
    def latest_status_display(self):
        return self.latest_status.label

    @property
    def latest_stat(self):
        return Status.get_terminal_latest_stat(self)

    @property
    def is_normal(self):
        return self.latest_status == StatusChoice.normal

    @property
    def is_high(self):
        return self.latest_status == StatusChoice.high

    @property
    def is_critical(self):
        return self.latest_status == StatusChoice.critical

    @property
    def is_alive(self):
        key = self.ALIVE_KEY.format(self.id)
        # return self.latest_status != StatusChoice.offline
        return cache.get(key, False)

    def set_alive(self, ttl=120):
        key = self.ALIVE_KEY.format(self.id)
        cache.set(key, True, ttl)


class StorageMixin:
    command_storage: str
    replay_storage: str

    def get_command_storage(self):
        from .storage import CommandStorage
        storage = CommandStorage.objects.filter(name=self.command_storage).first()
        return storage

    def get_command_storage_config(self):
        s = self.get_command_storage()
        if s:
            config = s.config
        else:
            config = settings.DEFAULT_TERMINAL_COMMAND_STORAGE
        return config

    def get_command_storage_setting(self):
        config = self.get_command_storage_config()
        return {"TERMINAL_COMMAND_STORAGE": config}

    def get_replay_storage(self):
        from .storage import ReplayStorage
        storage = ReplayStorage.objects.filter(name=self.replay_storage).first()
        return storage

    def get_replay_storage_config(self):
        s = self.get_replay_storage()
        if s:
            config = s.config
        else:
            config = settings.DEFAULT_TERMINAL_REPLAY_STORAGE
        return config

    def get_replay_storage_setting(self):
        config = self.get_replay_storage_config()
        return {"TERMINAL_REPLAY_STORAGE": config}


class Terminal(StorageMixin, TerminalStatusMixin, models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    type = models.CharField(
        choices=const.TerminalTypeChoices.choices, default=const.TerminalTypeChoices.koko.value,
        max_length=64, verbose_name=_('type')
    )
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

    def get_online_sessions(self):
        with tmp_to_root_org():
            return Session.objects.filter(terminal=self, is_finished=False)

    def get_online_session_count(self):
        return self.get_online_sessions().count()

    @staticmethod
    def get_login_title_setting():
        login_title = None
        if settings.XPACK_ENABLED:
            from xpack.plugins.interface.models import Interface
            login_title = Interface.get_login_title()
        return {'TERMINAL_HEADER_TITLE': login_title}

    @property
    def config(self):
        configs = {}
        for k in dir(settings):
            if not k.startswith('TERMINAL'):
                continue
            configs[k] = getattr(settings, k)
        configs.update(self.get_command_storage_setting())
        configs.update(self.get_replay_storage_setting())
        configs.update(self.get_login_title_setting())
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

