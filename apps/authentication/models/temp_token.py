from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel


class TempToken(JMSBaseModel):
    username = models.CharField(max_length=128, verbose_name=_("Username"))
    secret = models.CharField(max_length=64, verbose_name=_("Secret"))
    verified = models.BooleanField(default=False, verbose_name=_("Verified"))
    date_verified = models.DateTimeField(null=True, verbose_name=_("Date verified"))
    date_expired = models.DateTimeField(verbose_name=_("Date expired"))

    class Meta:
        verbose_name = _("Temporary token")

    @property
    def user(self):
        from users.models import User
        return User.objects.filter(username=self.username).first()

    @property
    def is_valid(self):
        not_expired = self.date_expired and self.date_expired > timezone.now()
        return not self.verified and not_expired
