import uuid

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.const.signals import SKIP_SIGNAL
from common.db.models import JMSBaseModel
from common.utils import get_logger, lazyproperty
from orgs.utils import tmp_to_root_org
from terminal.const import TerminalType as TypeChoices
from users.models import User
from .status import Status
from ..session import Session

logger = get_logger(__file__)


class TerminalStatusMixin:
    id: str
    type: str
    ALIVE_KEY = 'TERMINAL_ALIVE_{}'
    status_set: models.Manager

    @lazyproperty
    def last_stat(self):
        return Status.get_terminal_latest_stat(self)

    @lazyproperty
    def load(self):
        from ...utils import ComputeLoadUtil
        return ComputeLoadUtil.compute_load(self.last_stat, self.type)

    @property
    def is_alive(self):
        key = self.ALIVE_KEY.format(self.id)
        return cache.get(key, False)

    def set_alive(self, ttl=60 * 3):
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
            config = s.valid_config
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


class Terminal(StorageMixin, TerminalStatusMixin, JMSBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    type = models.CharField(
        choices=TypeChoices.choices, default=TypeChoices.koko,
        max_length=64, verbose_name=_('type')
    )
    remote_addr = models.CharField(max_length=128, blank=True, verbose_name=_('Remote Address'))
    command_storage = models.CharField(max_length=128, verbose_name=_("Command storage"), default='default')
    replay_storage = models.CharField(max_length=128, verbose_name=_("Replay storage"), default='default')
    user = models.OneToOneField(User, related_name='terminal', verbose_name=_('Application User'), null=True,
                                on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False)

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
        from settings.utils import get_login_title
        return {'TERMINAL_HEADER_TITLE': get_login_title()}

    @staticmethod
    def get_chat_ai_setting():
        return {
            'GPT_BASE_URL': settings.GPT_BASE_URL,
            'GPT_API_KEY': settings.GPT_API_KEY,
            'GPT_PROXY': settings.GPT_PROXY,
            'GPT_MODEL': settings.GPT_MODEL,
        }

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
        configs.update(self.get_chat_ai_setting())
        configs.update({
            'SECURITY_MAX_IDLE_TIME': settings.SECURITY_MAX_IDLE_TIME,
            'SECURITY_SESSION_SHARE': settings.SECURITY_SESSION_SHARE,
            'FTP_FILE_MAX_STORE': settings.FTP_FILE_MAX_STORE,
            'SECURITY_MAX_SESSION_TIME': settings.SECURITY_MAX_SESSION_TIME,
        })
        return configs

    @property
    def service_account(self):
        return self.user

    def delete(self, using=None, keep_parents=False):
        if self.user:
            setattr(self.user, SKIP_SIGNAL, True)
            self.user.delete()
        self.name = self.name + '_' + uuid.uuid4().hex[:8]
        self.user = None
        self.is_deleted = True
        self.save()
        return

    def __str__(self):
        status = "Active"
        if self.is_deleted:
            status = "Deleted"
        elif not self.is_active:
            status = "Disable"
        elif not self.is_alive:
            status = 'Offline'
        return '%s: %s' % (self.name, status)

    class Meta:
        db_table = "terminal"
        verbose_name = _("Terminal")
        permissions = (
            ('view_terminalconfig', _('Can view terminal config')),
        )
