from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models import TextChoices
import uuid
from ipaddress import ip_network
from orgs.mixins.models import OrgModelMixin


class PolicyActionChoices(TextChoices):
    deny = 'deny', _('Deny')
    confirm = 'confirm', _('Confirm')


class PolicyTypeChoices(TextChoices):
    asset = 'policy_asset', 'policy_asset'


class BaseACLPolicy(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    policy_type = models.CharField(max_length=32, choices=PolicyTypeChoices.choices,
                                   default=PolicyTypeChoices.asset, verbose_name=_('Policy Type'))
    action = models.CharField(max_length=32, choices=PolicyActionChoices.choices,
                              default=PolicyActionChoices.confirm, verbose_name=_("Action"))
    created_by = models.CharField(max_length=128, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    comment = models.TextField(verbose_name=_('Comment'), blank=True)
    # * 代表所有用户
    user = models.CharField(max_length=128, verbose_name=_('User'))

    class Meta:
        abstract = True


class AssetACLPolicy(BaseACLPolicy):
    ip = models.CharField(max_length=128, verbose_name=_('IP'), validators=[ip_network])
    ip_start = models.GenericIPAddressField(verbose_name=_('IP Start'))
    ip_end = models.GenericIPAddressField(verbose_name=_('IP End'))
    port = models.IntegerField(default=22, verbose_name=_('Port'))
    # * 代表所有系统用户
    system_user = models.CharField(max_length=128, verbose_name=_('System User'))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    reviewers = models.ManyToManyField('users.User', verbose_name=_("Reviewers"), related_name='%(class)ss')

    def save(self, *args, **kwargs):
        ip_net = ip_network(self.ip)
        self.ip_start = str(ip_net[0])
        self.ip_end = str(ip_net[-1])
        super(AssetACLPolicy, self).save(args, kwargs)

    def __str__(self):
        return self.ip
