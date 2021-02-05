from __future__ import unicode_literals
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.cache import cache

from common.utils import get_logger
from users.models import User
from .. import const


logger = get_logger(__file__)


class ComputeStatusMixin:

    # system status
    @staticmethod
    def _common_compute_system_status(value, thresholds):
        if thresholds[0] <= value <= thresholds[1]:
            return const.ComponentStatusChoices.normal.value
        elif thresholds[1] < value <= thresholds[2]:
            return const.ComponentStatusChoices.high.value
        else:
            return const.ComponentStatusChoices.critical.value

    def _compute_system_cpu_load_1_status(self, value):
        thresholds = [0, 5, 20]
        return self._common_compute_system_status(value, thresholds)

    def _compute_system_memory_used_percent_status(self, value):
        thresholds = [0, 85, 95]
        return self._common_compute_system_status(value, thresholds)

    def _compute_system_disk_used_percent_status(self, value):
        thresholds = [0, 80, 99]
        return self._common_compute_system_status(value, thresholds)

    def _compute_system_status(self, state):
        system_status_keys = [
            'system_cpu_load_1', 'system_memory_used_percent', 'system_disk_used_percent'
        ]
        system_status = []
        for system_status_key in system_status_keys:
            state_value = state.get(system_status_key)
            if state_value is None:
                msg = 'state: {}, state_key: {}, state_value: {}'
                logger.debug(msg.format(state, system_status_key, state_value))
                state_value = 0
            status = getattr(self, f'_compute_{system_status_key}_status')(state_value)
            system_status.append(status)
        return system_status

    def _compute_component_status(self, state):
        system_status = self._compute_system_status(state)
        if const.ComponentStatusChoices.critical in system_status:
            return const.ComponentStatusChoices.critical
        elif const.ComponentStatusChoices.high in system_status:
            return const.ComponentStatusChoices.high
        else:
            return const.ComponentStatusChoices.normal

    @staticmethod
    def _compute_component_status_display(status):
        return getattr(const.ComponentStatusChoices, status).label


class TerminalStateMixin(ComputeStatusMixin):
    CACHE_KEY_COMPONENT_STATE = 'CACHE_KEY_COMPONENT_STATE_TERMINAL_{}'
    CACHE_TIMEOUT = 120

    @property
    def cache_key(self):
        return self.CACHE_KEY_COMPONENT_STATE.format(str(self.id))

    # get
    def _get_from_cache(self):
        return cache.get(self.cache_key)

    def _set_to_cache(self, state):
        cache.set(self.cache_key, state, self.CACHE_TIMEOUT)

    # set
    def _add_status(self, state):
        status = self._compute_component_status(state)
        status_display = self._compute_component_status_display(status)
        state.update({
            'status': status,
            'status_display': status_display
        })

    @property
    def state(self):
        state = self._get_from_cache()
        return state or {}

    @state.setter
    def state(self, state):
        self._add_status(state)
        self._set_to_cache(state)


class TerminalStatusMixin(TerminalStateMixin):

    # alive
    @property
    def is_alive(self):
        return bool(self.state)

    # status
    @property
    def status(self):
        if self.is_alive:
            return self.state['status']
        else:
            return const.ComponentStatusChoices.critical.value

    @property
    def status_display(self):
        return self._compute_component_status_display(self.status)

    @property
    def is_normal(self):
        return self.status == const.ComponentStatusChoices.normal.value

    @property
    def is_high(self):
        return self.status == const.ComponentStatusChoices.high.value

    @property
    def is_critical(self):
        return self.status == const.ComponentStatusChoices.critical.value


class Terminal(TerminalStatusMixin, models.Model):
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

