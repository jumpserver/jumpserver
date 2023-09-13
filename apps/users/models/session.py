import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _

from audits.const import LoginTypeChoices


class UserSession(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    ip = models.GenericIPAddressField(verbose_name=_("Login IP"))
    key = models.CharField(max_length=128, verbose_name=_("Session key"))
    city = models.CharField(max_length=254, blank=True, null=True, verbose_name=_("Login city"))
    user_agent = models.CharField(max_length=254, blank=True, null=True, verbose_name=_("User agent"))
    type = models.CharField(choices=LoginTypeChoices.choices, max_length=2, verbose_name=_("Login type"))
    backend = models.CharField(max_length=32, default="", verbose_name=_("Authentication backend"))
    date_created = models.DateTimeField(null=True, blank=True, verbose_name=_('Date created'))
    date_expired = models.DateTimeField(null=True, blank=True, verbose_name=_("Date expired"), db_index=True)
    user = models.ForeignKey(
        'users.User', verbose_name=_('User'), related_name='sessions', on_delete=models.CASCADE
    )

    def __str__(self):
        return '%s(%s)' % (self.user, self.ip)

    @property
    def backend_display(self):
        return gettext(self.backend)

    @classmethod
    def clear_expired_sessions(cls):
        cls.objects.filter(date_expired__lt=timezone.now()).delete()

    class Meta:
        ordering = ['-date_created']
        verbose_name = _('User session')
        permissions = [
            ('offline_usersession', _('Offline ussr session')),
        ]
