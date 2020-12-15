from __future__ import unicode_literals

import os
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.cache import cache

from assets.models import Asset
from orgs.mixins.models import OrgModelMixin
from common.db.models import ChoiceSet
from ..backends import get_multi_command_storage
from .terminal import Terminal


class Session(OrgModelMixin):
    class LOGIN_FROM(ChoiceSet):
        ST = 'ST', 'SSH Terminal'
        WT = 'WT', 'Web Terminal'

    class PROTOCOL(ChoiceSet):
        SSH = 'ssh', 'ssh'
        RDP = 'rdp', 'rdp'
        VNC = 'vnc', 'vnc'
        TELNET = 'telnet', 'telnet'
        MYSQL = 'mysql', 'mysql'
        ORACLE = 'oracle', 'oracle'
        MARIADB = 'mariadb', 'mariadb'
        POSTGRESQL = 'postgresql', 'postgresql'
        K8S = 'k8s', 'kubernetes'

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_("User"), db_index=True)
    user_id = models.CharField(blank=True, default='', max_length=36, db_index=True)
    asset = models.CharField(max_length=128, verbose_name=_("Asset"), db_index=True)
    asset_id = models.CharField(blank=True, default='', max_length=36, db_index=True)
    system_user = models.CharField(max_length=128, verbose_name=_("System user"), db_index=True)
    system_user_id = models.CharField(blank=True, default='', max_length=36, db_index=True)
    login_from = models.CharField(max_length=2, choices=LOGIN_FROM.choices, default="ST", verbose_name=_("Login from"))
    remote_addr = models.CharField(max_length=128, verbose_name=_("Remote addr"), blank=True, null=True)
    is_success = models.BooleanField(default=True, db_index=True)
    is_finished = models.BooleanField(default=False, db_index=True)
    has_replay = models.BooleanField(default=False, verbose_name=_("Replay"))
    has_command = models.BooleanField(default=False, verbose_name=_("Command"))
    terminal = models.ForeignKey(Terminal, null=True, on_delete=models.DO_NOTHING, db_constraint=False)
    protocol = models.CharField(choices=PROTOCOL.choices, default='ssh', max_length=16, db_index=True)
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
    def asset_obj(self):
        return Asset.objects.get(id=self.asset_id)

    @property
    def _date_start_first_has_replay_rdp_session(self):
        if self.__class__._DATE_START_FIRST_HAS_REPLAY_RDP_SESSION is None:
            instance = self.__class__.objects.filter(
                protocol='rdp', has_replay=True
            ).order_by('date_start').first()
            if not instance:
                date_start = timezone.now() - timezone.timedelta(days=365)
            else:
                date_start = instance.date_start
            self.__class__._DATE_START_FIRST_HAS_REPLAY_RDP_SESSION = date_start
        return self.__class__._DATE_START_FIRST_HAS_REPLAY_RDP_SESSION

    def can_replay(self):
        if self.has_replay:
            return True
        if self.date_start < self._date_start_first_has_replay_rdp_session:
            return True
        return False

    @property
    def can_join(self):
        _PROTOCOL = self.PROTOCOL
        if self.is_finished:
            return False
        if self.protocol in [_PROTOCOL.SSH, _PROTOCOL.TELNET, _PROTOCOL.K8S]:
            return True
        else:
            return False

    @property
    def db_protocols(self):
        _PROTOCOL = self.PROTOCOL
        return [_PROTOCOL.MYSQL, _PROTOCOL.MARIADB, _PROTOCOL.ORACLE, _PROTOCOL.POSTGRESQL]

    @property
    def can_terminate(self):
        _PROTOCOL = self.PROTOCOL
        if self.is_finished:
            return False
        if self.protocol in self.db_protocols:
            return False
        else:
            return True

    def save_replay_to_storage(self, f):
        local_path = self.get_local_path()
        try:
            name = default_storage.save(local_path, f)
        except OSError as e:
            return None, e

        if settings.SERVER_REPLAY_STORAGE:
            from ..tasks import upload_session_replay_to_external_storage
            upload_session_replay_to_external_storage.delay(str(self.id))
        return name, None

    @classmethod
    def set_sessions_active(cls, sessions_id):
        data = {cls.ACTIVE_CACHE_KEY_PREFIX.format(i): i for i in sessions_id}
        cache.set_many(data, timeout=5*60)

    @classmethod
    def get_active_sessions(cls):
        return cls.objects.filter(is_finished=False)

    def is_active(self):
        key = self.ACTIVE_CACHE_KEY_PREFIX.format(self.id)
        return bool(cache.get(key))

    @property
    def command_amount(self):
        command_store = get_multi_command_storage()
        return command_store.count(session=str(self.id))

    @property
    def login_from_display(self):
        return self.get_login_from_display()

    @classmethod
    def generate_fake(cls, count=100, is_finished=True):
        import random
        from orgs.models import Organization
        from users.models import User
        from assets.models import Asset, SystemUser
        from orgs.utils import get_current_org
        from common.utils.random import random_datetime, random_ip

        org = get_current_org()
        if not org or not org.is_real():
            Organization.default().change_to()
        i = 0
        users = User.objects.all()[:100]
        assets = Asset.objects.all()[:100]
        system_users = SystemUser.objects.all()[:100]
        while i < count:
            user_random = random.choices(users, k=10)
            assets_random = random.choices(assets, k=10)
            system_users = random.choices(system_users, k=10)

            ziped = zip(user_random, assets_random, system_users)
            sessions = []
            now = timezone.now()
            month_ago = now - timezone.timedelta(days=30)
            for user, asset, system_user in ziped:
                ip = random_ip()
                date_start = random_datetime(month_ago, now)
                date_end = random_datetime(date_start, date_start+timezone.timedelta(hours=2))
                data = dict(
                    user=str(user), user_id=user.id,
                    asset=str(asset), asset_id=asset.id,
                    system_user=str(system_user), system_user_id=system_user.id,
                    remote_addr=ip,
                    date_start=date_start,
                    date_end=date_end,
                    is_finished=is_finished,
                )
                sessions.append(Session(**data))
            cls.objects.bulk_create(sessions)
            i += 10

    class Meta:
        db_table = "terminal_session"
        ordering = ["-date_start"]

    def __str__(self):
        return "{0.id} of {0.user} to {0.asset}".format(self)
