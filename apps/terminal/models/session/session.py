from __future__ import unicode_literals

import os
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from assets.models import Asset
from common.utils import get_object_or_none, lazyproperty
from orgs.mixins.models import OrgModelMixin
from terminal.backends import get_multi_command_storage
from terminal.const import SessionType, TerminalType
from users.models import User


class Session(OrgModelMixin):
    class LOGIN_FROM(models.TextChoices):
        ST = 'ST', 'SSH Terminal'
        RT = 'RT', 'RDP Terminal'
        WT = 'WT', 'Web Terminal'
        DT = 'DT', 'DB Terminal'

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_("User"), db_index=True)
    user_id = models.CharField(blank=True, default='', max_length=36, db_index=True)
    asset = models.CharField(max_length=128, verbose_name=_("Asset"), db_index=True)
    asset_id = models.CharField(blank=True, default='', max_length=36, db_index=True)
    account = models.CharField(max_length=128, verbose_name=_("Account"), db_index=True)
    account_id = models.CharField(max_length=128, verbose_name=_("Account id"), db_index=True)
    protocol = models.CharField(default='ssh', max_length=16, db_index=True)
    login_from = models.CharField(max_length=2, choices=LOGIN_FROM.choices, default="ST", verbose_name=_("Login from"))
    type = models.CharField(max_length=16, default='normal', db_index=True)
    remote_addr = models.CharField(max_length=128, verbose_name=_("Remote addr"), blank=True, null=True)
    is_success = models.BooleanField(default=True, db_index=True)
    is_finished = models.BooleanField(default=False, db_index=True)
    has_replay = models.BooleanField(default=False, verbose_name=_("Replay"))
    has_command = models.BooleanField(default=False, verbose_name=_("Command"))
    terminal = models.ForeignKey('terminal.Terminal', null=True, on_delete=models.DO_NOTHING, db_constraint=False)
    date_start = models.DateTimeField(verbose_name=_("Date start"), db_index=True, default=timezone.now)
    date_end = models.DateTimeField(verbose_name=_("Date end"), null=True)
    comment = models.TextField(blank=True, null=True, verbose_name=_("Comment"))
    cmd_amount = models.IntegerField(default=-1, verbose_name=_("Command amount"))
    error_reason = models.CharField(max_length=128, blank=True, verbose_name=_("Error reason"))

    upload_to = 'replay'
    ACTIVE_CACHE_KEY_PREFIX = 'SESSION_ACTIVE_{}'
    LOCK_CACHE_KEY_PREFIX = 'TOGGLE_LOCKED_SESSION_{}'
    SUFFIX_MAP = {1: '.gz', 2: '.replay.gz', 3: '.cast.gz', 4: '.replay.mp4'}
    DEFAULT_SUFFIXES = ['.replay.gz', '.cast.gz', '.gz', '.replay.mp4']

    # Todo: 将来干掉 local_path, 使用 default storage 实现
    def get_all_possible_local_path(self):
        """
        获取所有可能的本地存储录像文件路径
        :return:
        """
        return [self.get_local_storage_path_by_suffix(suffix)
                for suffix in self.SUFFIX_MAP.values()]

    def get_all_possible_relative_path(self):
        """
        获取所有可能的外部存储录像文件路径
        :return:
        """
        return [self.get_relative_path_by_suffix(suffix)
                for suffix in self.SUFFIX_MAP.values()]

    def get_local_storage_path_by_suffix(self, suffix='.cast.gz'):
        """
        local_path: replay/2021-12-08/session_id.cast.gz
        通过后缀名获取本地存储的录像文件路径
        :param suffix: .cast.gz | '.replay.gz' | '.gz'
        :return:
        """
        rel_path = self.get_relative_path_by_suffix(suffix)
        if suffix == '.gz':
            # 兼容 v1 的版本
            return rel_path
        return os.path.join(self.upload_to, rel_path)

    def get_relative_path_by_suffix(self, suffix='.cast.gz'):
        """
        relative_path: 2021-12-08/session_id.cast.gz
        通过后缀名获取外部存储录像文件路径
        :param suffix: .cast.gz | '.replay.gz' | '.gz'
        :return:
        """
        date = self.date_start.strftime('%Y-%m-%d')
        return os.path.join(date, str(self.id) + suffix)

    def get_local_path_by_relative_path(self, rel_path):
        """
        2021-12-08/session_id.cast.gz
        :param rel_path:
        :return: replay/2021-12-08/session_id.cast.gz
        """
        return '{}/{}'.format(self.upload_to, rel_path)

    def get_relative_path_by_local_path(self, local_path):
        return local_path.replace('{}/'.format(self.upload_to), '')

    def find_ok_relative_path_in_storage(self, storage):
        session_paths = self.get_all_possible_relative_path()
        for rel_path in session_paths:
            # storage 为多个外部存储时, 可能会因部分不可用，
            # 抛出异常, 影响录像的获取
            try:
                if storage.exists(rel_path):
                    return rel_path
            except:
                pass

    @property
    def asset_obj(self):
        return Asset.objects.get(id=self.asset_id)

    @property
    def user_obj(self):
        return User.objects.get(id=self.user_id)

    def can_replay(self):
        return self.has_replay

    @property
    def can_join(self):
        if self.is_finished:
            return False
        if self.login_from == self.LOGIN_FROM.RT:
            return False
        if self.type != SessionType.normal:
            # 会话监控仅支持 normal，不支持 tunnel 和 command
            return False
        if self.terminal.type in [TerminalType.lion, TerminalType.koko]:
            return True
        else:
            return False

    @property
    def can_terminate(self):
        if self.is_finished:
            return False
        else:
            return True

    @property
    def is_locked(self):
        if self.is_finished:
            return False
        key = self.LOCK_CACHE_KEY_PREFIX.format(self.id)
        return bool(cache.get(key))

    @classmethod
    def lock_session(cls, session_id):
        key = cls.LOCK_CACHE_KEY_PREFIX.format(session_id)
        # 会话锁定时间为 None，表示永不过期
        # You can set TIMEOUT to None so that, by default, cache keys never expire.
        # https://docs.djangoproject.com/en/4.1/topics/cache/
        cache.set(key, True, timeout=None)

    @classmethod
    def unlock_session(cls, session_id):
        key = cls.LOCK_CACHE_KEY_PREFIX.format(session_id)
        cache.delete(key)

    @lazyproperty
    def terminal_display(self):
        display = self.terminal.name if self.terminal else ''
        return display

    def save_replay_to_storage_with_version(self, f, version=2):
        suffix = self.SUFFIX_MAP.get(version, '.cast.gz')
        local_path = self.get_local_storage_path_by_suffix(suffix)
        try:
            name = default_storage.save(local_path, f)
        except OSError as e:
            return None, e

        if settings.SERVER_REPLAY_STORAGE:
            from terminal.tasks import upload_session_replay_to_external_storage
            upload_session_replay_to_external_storage.delay(str(self.id))
        return name, None

    @classmethod
    def set_sessions_active(cls, session_ids):
        data = {cls.ACTIVE_CACHE_KEY_PREFIX.format(i): i for i in session_ids}
        cache.set_many(data, timeout=5 * 60)

    @classmethod
    def get_active_sessions(cls):
        return cls.objects.filter(is_finished=False)

    def is_active(self):
        key = self.ACTIVE_CACHE_KEY_PREFIX.format(self.id)
        return bool(cache.get(key))

    @property
    def command_amount(self):
        if self.need_update_cmd_amount:
            cmd_amount = self.compute_command_amount()
            self.cmd_amount = cmd_amount
            self.save()
        elif self.need_compute_cmd_amount:
            cmd_amount = self.compute_command_amount()
        else:
            cmd_amount = self.cmd_amount
        return cmd_amount

    @property
    def need_update_cmd_amount(self):
        return self.is_finished and self.need_compute_cmd_amount

    @property
    def need_compute_cmd_amount(self):
        return self.cmd_amount == -1

    def compute_command_amount(self):
        command_store = get_multi_command_storage()
        return command_store.count(session=str(self.id))

    @property
    def login_from_display(self):
        return self.get_login_from_display()

    def get_asset(self):
        return get_object_or_none(Asset, pk=self.asset_id)

    def get_target_ip(self):
        instance = self.get_asset()
        target_ip = instance.get_target_ip() if instance else ''
        return target_ip

    @classmethod
    def generate_fake(cls, count=100, is_finished=True):
        import random
        from orgs.models import Organization
        from users.models import User
        from assets.models import Asset, SystemUser
        from orgs.utils import get_current_org
        from common.utils.random import random_datetime, random_ip

        org = get_current_org()
        if not org or org.is_root():
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
                date_end = random_datetime(date_start, date_start + timezone.timedelta(hours=2))
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
        verbose_name = _('Session record')
        permissions = [
            ('monitor_session', _('Can monitor session')),
            ('share_session', _('Can share session')),
            ('terminate_session', _('Can terminate session')),
            ('validate_sessionactionperm', _('Can validate session action perm')),
        ]

    def __str__(self):
        return "{0.id} of {0.user} to {0.asset}".format(self)
