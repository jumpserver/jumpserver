import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _
from rest_framework.authtoken.models import Token
from django.conf import settings

from common.mixins.models import CommonModelMixin


class AccessKey(models.Model):
    id = models.UUIDField(verbose_name='AccessKeyID', primary_key=True,
                          default=uuid.uuid4, editable=False)
    secret = models.UUIDField(verbose_name='AccessKeySecret',
                              default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='User',
                             on_delete=models.CASCADE, related_name='access_keys')
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    date_created = models.DateTimeField(auto_now_add=True)

    def get_id(self):
        return str(self.id)

    def get_secret(self):
        return str(self.secret)

    def get_full_value(self):
        return '{}:{}'.format(self.id, self.secret)

    def __str__(self):
        return str(self.id)


class PrivateToken(Token):
    """Inherit from auth token, otherwise migration is boring"""

    class Meta:
        verbose_name = _('Private Token')


class LoginConfirmSetting(CommonModelMixin):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, verbose_name=_("User"), related_name=_("login_confirmation_setting"))
    reviewers = models.ManyToManyField('users.User', verbose_name=_("Reviewers"), related_name=_("review_login_confirmation_settings"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

