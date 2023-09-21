import datetime

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property

from common.db.models import JMSBaseModel
from common.utils import is_uuid
from orgs.mixins.models import OrgModelMixin
from orgs.utils import tmp_to_root_org
from users.models import User
from .session import Session

__all__ = ['SessionSharing', 'SessionJoinRecord']


class SessionSharing(JMSBaseModel, OrgModelMixin):
    session = models.ForeignKey(
        'terminal.Session', on_delete=models.CASCADE, verbose_name=_('Session')
    )
    # creator / created_by
    creator = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, blank=True, null=True,
        verbose_name=_('Creator')
    )
    verify_code = models.CharField(max_length=16, verbose_name=_('Verify code'))
    is_active = models.BooleanField(
        default=True, verbose_name=_('Active'), db_index=True
    )
    expired_time = models.IntegerField(
        default=0, verbose_name=_('Expired time (min)'), db_index=True
    )
    users = models.TextField(blank=True, verbose_name=_("User"))
    action_permission = models.CharField(
        max_length=16, verbose_name=_('Action permission'), default='writable'
    )
    origin = models.URLField(blank=True, null=True, verbose_name=_('Origin'))

    class Meta:
        ordering = ('-date_created',)
        verbose_name = _('Session sharing')
        permissions = [
            ('add_supersessionsharing', _("Can add super session sharing"))
        ]

    def __str__(self):
        return 'Creator: {}'.format(self.creator)

    @cached_property
    def url(self):
        return '%s/koko/share/%s/' % (self.origin, self.id)

    @cached_property
    def users_display(self):
        if not self.users:
            return []
        with tmp_to_root_org():
            users = self.users_queryset
            users = [str(user) for user in users]
        return users

    @cached_property
    def users_queryset(self):
        user_ids = self.users.split(',')
        user_ids = [user_id for user_id in user_ids if is_uuid(user_id)]
        if not user_ids:
            return User.objects.none()
        return User.objects.filter(id__in=user_ids)

    @property
    def date_expired(self):
        return self.date_created + datetime.timedelta(minutes=self.expired_time)

    @property
    def is_expired(self):
        if timezone.now() > self.date_expired:
            return False
        return True

    def can_join(self, joiner):
        if not self.is_active:
            return False, _('Link not active')
        if not self.is_expired:
            return False, _('Link expired')
        if self.users and str(joiner.id) not in self.users.split(','):
            return False, _('User not allowed to join')
        return True, ''


class SessionJoinRecord(JMSBaseModel, OrgModelMixin):
    LOGIN_FROM = Session.LOGIN_FROM

    session = models.ForeignKey(
        'terminal.Session', on_delete=models.CASCADE, verbose_name=_('Session')
    )
    verify_code = models.CharField(max_length=16, verbose_name=_('Verify code'))
    sharing = models.ForeignKey(
        SessionSharing, on_delete=models.CASCADE,
        verbose_name=_('Session sharing')
    )
    joiner = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, blank=True, null=True,
        verbose_name=_('Joiner')
    )
    date_joined = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Date joined"), db_index=True,
    )
    date_left = models.DateTimeField(
        verbose_name=_("Date left"), null=True, db_index=True
    )
    remote_addr = models.CharField(
        max_length=128, verbose_name=_("Remote addr"), blank=True, null=True,
        db_index=True
    )
    login_from = models.CharField(
        max_length=2, choices=LOGIN_FROM.choices, default="WT",
        verbose_name=_("Login from")
    )
    is_success = models.BooleanField(
        default=True, db_index=True, verbose_name=_('Success')
    )
    reason = models.CharField(
        max_length=1024, default='-', blank=True, null=True,
        verbose_name=_('Reason')
    )
    is_finished = models.BooleanField(
        default=False, db_index=True, verbose_name=_('Finished')
    )

    class Meta:
        ordering = ('-date_joined',)
        verbose_name = _("Session join record")

    def __str__(self):
        return 'Joiner: {}'.format(self.joiner)

    @property
    def joiner_display(self):
        return str(self.joiner)

    def can_join(self):
        # sharing
        sharing_can_join, reason = self.sharing.can_join(self.joiner)
        if not sharing_can_join:
            return False, reason
        # self
        if self.verify_code != self.sharing.verify_code:
            return False, _('Invalid verification code')

        # Link can only be joined once by the same user.
        queryset = SessionJoinRecord.objects.filter(
            verify_code=self.verify_code, sharing=self.sharing,
            joiner=self.joiner, date_joined__lt=self.date_joined)
        if queryset.exists():
            return False, _('You have already joined this session')
        return True, ''

    def join_failed(self, reason):
        self.is_success = False
        self.reason = reason[:1024]
        self.save()

    def finished(self):
        if self.is_finished:
            return
        self.date_left = timezone.now()
        self.is_finished = True
        self.save()

    @property
    def action_permission(self):
        return self.sharing.action_permission
