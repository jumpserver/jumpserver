import uuid

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from orgs.mixins import OrgModelMixin

__all__ = [
    'FTPLog', 'OperateLog', 'PasswordChangeLog', 'UserLoginLog',
]


class FTPLog(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_('User'))
    remote_addr = models.CharField(max_length=15, verbose_name=_("Remote addr"), blank=True, null=True)
    asset = models.CharField(max_length=1024, verbose_name=_("Asset"))
    system_user = models.CharField(max_length=128, verbose_name=_("System user"))
    operate = models.CharField(max_length=16, verbose_name=_("Operate"))
    filename = models.CharField(max_length=1024, verbose_name=_("Filename"))
    is_success = models.BooleanField(default=True, verbose_name=_("Success"))
    date_start = models.DateTimeField(auto_now_add=True)


class OperateLog(OrgModelMixin):
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_CHOICES = (
        (ACTION_CREATE, _("Create")),
        (ACTION_UPDATE, _("Update")),
        (ACTION_DELETE, _("Delete"))
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_('User'))
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, verbose_name=_("Action"))
    resource_type = models.CharField(max_length=64, verbose_name=_("Resource Type"))
    resource = models.CharField(max_length=128, verbose_name=_("Resource"))
    remote_addr = models.CharField(max_length=15, verbose_name=_("Remote addr"), blank=True, null=True)
    datetime = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "<{}> {} <{}>".format(self.user, self.action, self.resource)


class PasswordChangeLog(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_('User'))
    change_by = models.CharField(max_length=128, verbose_name=_("Change by"))
    remote_addr = models.CharField(max_length=15, verbose_name=_("Remote addr"), blank=True, null=True)
    datetime = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} change {}'s password".format(self.change_by, self.user)


class UserLoginLog(models.Model):
    LOGIN_TYPE_CHOICE = (
        ('W', 'Web'),
        ('T', 'Terminal'),
    )

    MFA_DISABLED = 0
    MFA_ENABLED = 1
    MFA_UNKNOWN = 2

    MFA_CHOICE = (
        (MFA_DISABLED, _('Disabled')),
        (MFA_ENABLED, _('Enabled')),
        (MFA_UNKNOWN, _('-')),
    )

    REASON_NOTHING = 0
    REASON_PASSWORD = 1
    REASON_MFA = 2
    REASON_NOT_EXIST = 3
    REASON_PASSWORD_EXPIRED = 4

    REASON_CHOICE = (
        (REASON_NOTHING, _('-')),
        (REASON_PASSWORD, _('Username/password check failed')),
        (REASON_MFA, _('MFA authentication failed')),
        (REASON_NOT_EXIST, _("Username does not exist")),
        (REASON_PASSWORD_EXPIRED, _("Password expired")),
    )

    STATUS_CHOICE = (
        (True, _('Success')),
        (False, _('Failed'))
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    username = models.CharField(max_length=128, verbose_name=_('Username'))
    type = models.CharField(choices=LOGIN_TYPE_CHOICE, max_length=2, verbose_name=_('Login type'))
    ip = models.GenericIPAddressField(verbose_name=_('Login ip'))
    city = models.CharField(max_length=254, blank=True, null=True, verbose_name=_('Login city'))
    user_agent = models.CharField(max_length=254, blank=True, null=True, verbose_name=_('User agent'))
    mfa = models.SmallIntegerField(default=MFA_UNKNOWN, choices=MFA_CHOICE, verbose_name=_('MFA'))
    reason = models.SmallIntegerField(default=0, choices=REASON_CHOICE, verbose_name=_('Reason'))
    status = models.BooleanField(max_length=2, default=True, choices=STATUS_CHOICE, verbose_name=_('Status'))
    datetime = models.DateTimeField(default=timezone.now, verbose_name=_('Date login'))

    @classmethod
    def get_login_logs(cls, date_form=None, date_to=None, user=None, keyword=None):
        login_logs = cls.objects.all()
        if date_form and date_to:
            login_logs = login_logs.filter(
                datetime__gt=date_form, datetime__lt=date_to
            )
        if user:
            login_logs = login_logs.filter(username=user)
        if keyword:
            login_logs = login_logs.filter(
                Q(ip__contains=keyword) |
                Q(city__contains=keyword) |
                Q(username__contains=keyword)
            )
        return login_logs

    class Meta:
        ordering = ['-datetime', 'username']
