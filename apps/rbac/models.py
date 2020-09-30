from django.utils.translation import ugettext_lazy as _

from common.db import models


class Role(models.JMSModel):
    class TypeChoices(models.ChoiceSet):
        system = 'system', _('System')
        org = 'org', _('Organization')
        namespace = 'namespace', _('Namespace')
        common = 'common', _('Common')

    name = models.CharField(max_length=256, verbose_name=_('Role name'))
    type = models.CharField(max_length=64, default=TypeChoices.common,
                            choices=TypeChoices.choices, verbose_name=_('Role type'))
    permissions = models.ManyToManyField('auth.Permission', verbose_name=_('Permissions'))
    is_build_in = models.BooleanField(default=False, verbose_name=_('Is build in'))

    def __str__(self):
        return self.name


class RoleBinding(models.JMSModel):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))
    role = models.ForeignKey(Role, on_delete=models.PROTECT, verbose_name=_('Role'))
    namespaces = models.ManyToManyField('namespaces.Namespace', verbose_name=_('Namespaces'))
    orgs = models.ManyToManyField('orgs.Organization', verbose_name=_('Organizations'))
    date_expired = models.DateTimeField(verbose_name=_('Date expired'))

    class Meta:
        unique_together = [('user', 'role')]
