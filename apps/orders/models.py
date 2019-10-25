from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin


class Order(CommonModelMixin):
    STATUS_CHOICES = (
        ('accepted', _("Accepted")),
        ('rejected', _("Rejected")),
        ('pending', _("Pending"))
    )
    TYPE_CHOICES = (
        ('login_request', _("Login request")),
    )
    requester = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='orders')
    user_name = models.CharField(max_length=128, verbose_name=_("User"))
    title = models.CharField(max_length=256, verbose_name=_("Title"))
    body = models.TextField(verbose_name=_("Body"))

    type = models.CharField(choices=TYPE_CHOICES, max_length=64)
    status = models.CharField(choices=STATUS_CHOICES, max_length=16)

