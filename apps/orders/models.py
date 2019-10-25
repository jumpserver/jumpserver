from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin


class Order(CommonModelMixin):
    STATUS_CHOICES = (
        ('accepted', _("Accepted")),
        ('rejected', _("Rejected")),
        ('pending', _("Pending"))
    )
    TYPE_LOGIN_REQUEST = 'login_request'
    TYPE_CHOICES = (
        (TYPE_LOGIN_REQUEST, _("Login request")),
    )
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='orders', verbose_name=_("User"))
    user_display = models.CharField(max_length=128, verbose_name=_("User display name"))

    title = models.CharField(max_length=256, verbose_name=_("Title"))
    body = models.TextField(verbose_name=_("Body"))
    assignees = models.ManyToManyField('users.User', related_name='assign_orders', verbose_name=_("Assignees"))
    assignees_display = models.CharField(max_length=128, verbose_name=_("Assignees display name"), blank=True)

    type = models.CharField(choices=TYPE_CHOICES, max_length=64)
    status = models.CharField(choices=STATUS_CHOICES, max_length=16, default='pending')

    def __str__(self):
        return '{}: {}'.format(self.user_display, self.title)

    class Meta:
        ordering = ('date_created',)

