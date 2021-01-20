import uuid

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, ugettext as __
from rest_framework.authtoken.models import Token
from django.conf import settings

from common.db import models
from common.mixins.models import CommonModelMixin
from common.utils import get_object_or_none, get_request_ip, get_ip_city


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
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, verbose_name=_("User"), related_name="login_confirm_setting")
    reviewers = models.ManyToManyField('users.User', verbose_name=_("Reviewers"), related_name="review_login_confirm_settings", blank=True)
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    @classmethod
    def get_user_confirm_setting(cls, user):
        return get_object_or_none(cls, user=user)

    @staticmethod
    def construct_confirm_ticket_meta(request=None):
        if request:
            login_ip = get_request_ip(request)
        else:
            login_ip = ''
        login_ip = login_ip or '0.0.0.0'
        login_city = get_ip_city(login_ip)
        login_datetime = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        ticket_meta = {
            'apply_login_ip': login_ip,
            'apply_login_city': login_city,
            'apply_login_datetime': login_datetime,
        }
        return ticket_meta

    def create_confirm_ticket(self, request=None):
        from tickets import const
        from tickets.models import Ticket
        ticket_title = _('Login confirm') + ' {}'.format(self.user)
        ticket_meta = self.construct_confirm_ticket_meta(request)
        ticket_assignees = self.reviewers.all()
        data = {
            'title': ticket_title,
            'type': const.TicketTypeChoices.login_confirm.value,
            'meta': ticket_meta,
        }
        ticket = Ticket.objects.create(**data)
        ticket.assignees.set(ticket_assignees)
        ticket.open(self.user)
        return ticket

    def __str__(self):
        return '{} confirm'.format(self.user.username)


class SSOToken(models.JMSBaseModel):
    """
    类似腾讯企业邮的 [单点登录](https://exmail.qq.com/qy_mng_logic/doc#10036)
    出于安全考虑，这里的 `token` 使用一次随即过期。但我们保留每一个生成过的 `token`。
    """
    authkey = models.UUIDField(primary_key=True, default=uuid.uuid4, verbose_name=_('Token'))
    expired = models.BooleanField(default=False, verbose_name=_('Expired'))
    user = models.ForeignKey('users.User', on_delete=models.PROTECT, verbose_name=_('User'), db_constraint=False)
