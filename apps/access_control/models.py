from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgModelMixin


class AccessControl(OrgModelMixin):
    name = models.CharField(max_length=512, verbose_name=_('name'))
    ips = models.CharField(max_length=512, verbose_name=_('IPs'))
    date_from = models.DateTimeField(verbose_name=_('Date from'))
    date_to = models.DateTimeField(verbose_name=_('Date to'))
    users = models.ManyToManyField('users.User', related_name='login_policies', verbose_name=_('Users'))

    def get_absolute_url(self):
        return reverse('api-access-control:access-control-detail', args=(self.id,))
