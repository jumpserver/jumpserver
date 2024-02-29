import os
import uuid
from datetime import timedelta
from importlib import import_module

from django.conf import settings
from django.core.cache import caches
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _

from common.db.encoder import ModelJSONFieldEncoder
from common.sessions.cache import user_session_manager
from common.utils import lazyproperty, i18n_trans
from ops.models import JobExecution
from orgs.mixins.models import OrgModelMixin, Organization
from orgs.utils import current_org
from terminal.models import default_storage
from .const import (
    OperateChoices,
    ActionChoices,
    ActivityChoices,
    LoginTypeChoices,
    MFAChoices,
    LoginStatusChoices,
)

__all__ = [
    "FTPLog",
    "OperateLog",
    "ActivityLog",
    "PasswordChangeLog",
    "UserLoginLog",
    "JobLog",
    "UserSession"
]


class JobLog(JobExecution):
    @property
    def creator_name(self):
        return self.creator.name

    class Meta:
        proxy = True
        verbose_name = _("Job audit log")


class FTPLog(OrgModelMixin):
    upload_to = 'FTP_FILES'

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_("User"))
    remote_addr = models.CharField(
        max_length=128, verbose_name=_("Remote addr"), blank=True, null=True
    )
    asset = models.CharField(max_length=1024, verbose_name=_("Asset"))
    account = models.CharField(max_length=128, verbose_name=_("Account"))
    operate = models.CharField(
        max_length=16, verbose_name=_("Operate"), choices=OperateChoices.choices
    )
    filename = models.CharField(max_length=1024, verbose_name=_("Filename"))
    is_success = models.BooleanField(default=True, verbose_name=_("Success"))
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_("Date start"), db_index=True)
    has_file = models.BooleanField(default=False, verbose_name=_("File"))
    session = models.CharField(max_length=36, verbose_name=_("Session"), default=uuid.uuid4)

    class Meta:
        verbose_name = _("File transfer log")

    @property
    def filepath(self):
        return os.path.join(self.upload_to, self.date_start.strftime('%Y-%m-%d'), str(self.id))

    def save_file_to_storage(self, file):
        try:
            name = default_storage.save(self.filepath, file)
        except OSError as e:
            return None, e

        if settings.SERVER_REPLAY_STORAGE:
            from .tasks import upload_ftp_file_to_external_storage
            upload_ftp_file_to_external_storage.delay(str(self.id), file.name)
        return name, None


class OperateLog(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_("User"))
    action = models.CharField(
        max_length=16, choices=ActionChoices.choices, verbose_name=_("Action")
    )
    resource_type = models.CharField(max_length=64, verbose_name=_("Resource Type"))
    resource = models.CharField(max_length=128, verbose_name=_("Resource"))
    resource_id = models.CharField(
        max_length=128, blank=True, default='', db_index=True,
        verbose_name=_("Resource")
    )
    remote_addr = models.CharField(max_length=128, verbose_name=_("Remote addr"), blank=True, null=True)
    datetime = models.DateTimeField(auto_now=True, verbose_name=_('Datetime'), db_index=True)
    diff = models.JSONField(default=dict, encoder=ModelJSONFieldEncoder, null=True)

    def __str__(self):
        return "<{}> {} <{}>".format(self.user, self.action, self.resource)

    @lazyproperty
    def resource_type_display(self):
        return gettext(self.resource_type)

    def save(self, *args, **kwargs):
        if current_org.is_root() and not self.org_id:
            self.org_id = Organization.ROOT_ID
        return super(OperateLog, self).save(*args, **kwargs)

    @classmethod
    def from_dict(cls, d):
        self = cls()
        for k, v in d.items():
            setattr(self, k, v)
        return self

    @classmethod
    def from_multi_dict(cls, l):
        operate_logs = []
        for d in l:
            operate_log = cls.from_dict(d)
            operate_logs.append(operate_log)
        return operate_logs

    class Meta:
        verbose_name = _("Operate log")
        ordering = ('-datetime',)


class ActivityLog(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    type = models.CharField(
        choices=ActivityChoices.choices, max_length=2,
        null=True, default=None, verbose_name=_("Activity type"),
    )
    resource_id = models.CharField(
        max_length=36, blank=True, default='',
        db_index=True, verbose_name=_("Resource")
    )
    datetime = models.DateTimeField(
        auto_now=True, verbose_name=_('Datetime'), db_index=True
    )
    # 日志的描述信息
    detail = models.TextField(default='', blank=True, verbose_name=_('Detail'))
    # 详情ID, 结合 type 来使用, (实例ID 和 CeleryTaskID)
    detail_id = models.CharField(
        max_length=36, default=None, null=True, verbose_name=_('Detail ID')
    )

    class Meta:
        verbose_name = _("Activity log")
        ordering = ('-datetime',)

    def __str__(self):
        detail = i18n_trans(self.detail)
        return "{} {}".format(detail, self.resource_id)

    def save(self, *args, **kwargs):
        if current_org.is_root() and not self.org_id:
            self.org_id = Organization.ROOT_ID
        return super(ActivityLog, self).save(*args, **kwargs)


class PasswordChangeLog(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_("User"))
    change_by = models.CharField(max_length=128, verbose_name=_("Change by"))
    remote_addr = models.CharField(
        max_length=128, verbose_name=_("Remote addr"), blank=True, null=True
    )
    datetime = models.DateTimeField(auto_now=True, verbose_name=_("Datetime"))

    def __str__(self):
        return "{} change {}'s password".format(self.change_by, self.user)

    class Meta:
        verbose_name = _("Password change log")


class UserLoginLog(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    username = models.CharField(max_length=128, verbose_name=_("Username"))
    type = models.CharField(
        choices=LoginTypeChoices.choices, max_length=2, verbose_name=_("Login type")
    )
    ip = models.GenericIPAddressField(verbose_name=_("Login IP"))
    city = models.CharField(
        max_length=254, blank=True, null=True, verbose_name=_("Login city")
    )
    user_agent = models.CharField(
        max_length=254, blank=True, null=True, verbose_name=_("User agent")
    )
    mfa = models.SmallIntegerField(
        default=MFAChoices.unknown, choices=MFAChoices.choices, verbose_name=_("MFA")
    )
    reason = models.CharField(
        default="", max_length=128, blank=True, verbose_name=_("Reason")
    )
    status = models.BooleanField(
        default=LoginStatusChoices.success,
        choices=LoginStatusChoices.choices,
        verbose_name=_("Status"),
    )
    datetime = models.DateTimeField(default=timezone.now, verbose_name=_("Date login"), db_index=True)
    backend = models.CharField(
        max_length=32, default="", verbose_name=_("Authentication backend")
    )

    def __str__(self):
        return '%s(%s)' % (self.username, self.city)

    @property
    def backend_display(self):
        return gettext(self.backend)

    @classmethod
    def get_login_logs(cls, date_from=None, date_to=None, user=None, keyword=None):
        login_logs = cls.objects.all()
        if date_from and date_to:
            date_from = "{} {}".format(date_from, "00:00:00")
            date_to = "{} {}".format(date_to, "23:59:59")
            login_logs = login_logs.filter(
                datetime__gte=date_from, datetime__lte=date_to
            )
        if user:
            login_logs = login_logs.filter(username=user)
        if keyword:
            login_logs = login_logs.filter(
                Q(ip__contains=keyword)
                | Q(city__contains=keyword)
                | Q(username__contains=keyword)
            )
        if not current_org.is_root():
            username_list = current_org.get_members().values_list("username", flat=True)
            login_logs = login_logs.filter(username__in=username_list)
        return login_logs

    @property
    def reason_display(self):
        from authentication.errors import reason_choices, old_reason_choices

        reason = reason_choices.get(self.reason)
        if reason:
            return reason
        reason = old_reason_choices.get(self.reason, self.reason)
        return reason

    class Meta:
        ordering = ["-datetime", "username"]
        verbose_name = _("User login log")


class UserSession(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    ip = models.GenericIPAddressField(verbose_name=_("Login IP"))
    key = models.CharField(max_length=128, verbose_name=_("Session key"))
    city = models.CharField(max_length=254, blank=True, null=True, verbose_name=_("Login city"))
    user_agent = models.CharField(max_length=254, blank=True, null=True, verbose_name=_("User agent"))
    type = models.CharField(choices=LoginTypeChoices.choices, max_length=2, verbose_name=_("Login type"))
    backend = models.CharField(max_length=32, default="", verbose_name=_("Authentication backend"))
    date_created = models.DateTimeField(null=True, blank=True, verbose_name=_('Date created'))
    user = models.ForeignKey(
        'users.User', verbose_name=_('User'), related_name='sessions', on_delete=models.CASCADE
    )

    def __str__(self):
        return '%s(%s)' % (self.user, self.ip)

    @property
    def backend_display(self):
        return gettext(self.backend)

    @property
    def is_active(self):
        return user_session_manager.check_active(self.key)

    @property
    def date_expired(self):
        session_store_cls = import_module(settings.SESSION_ENGINE).SessionStore
        session_store = session_store_cls(session_key=self.key)
        cache_key = session_store.cache_key
        ttl = caches[settings.SESSION_CACHE_ALIAS].ttl(cache_key)
        return timezone.now() + timedelta(seconds=ttl)

    @staticmethod
    def get_keys():
        session_store_cls = import_module(settings.SESSION_ENGINE).SessionStore
        cache_key_prefix = session_store_cls.cache_key_prefix
        keys = caches[settings.SESSION_CACHE_ALIAS].iter_keys('*')
        return [k.replace(cache_key_prefix, '') for k in keys]

    @classmethod
    def clear_expired_sessions(cls):
        keys = cls.get_keys()
        cls.objects.exclude(key__in=keys).delete()

    class Meta:
        ordering = ['-date_created']
        verbose_name = _('User session')
        permissions = [
            ('offline_usersession', _('Offline user session')),
        ]
