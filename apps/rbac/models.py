from django.utils.translation import ugettext_lazy as _

from common.db import models


class Role(models.JMSModel):
    class TypeChoices(models.ChoiceSet):
        system = 'system', _('System role')
        org = 'org', _('Organization role')
        namespace = 'namespace', _('Namespace role')

    name = models.CharField(max_length=256, verbose_name=_('Role name'))
    type = models.CharField(max_length=64, default=TypeChoices.namespace,
                            choices=TypeChoices.choices, verbose_name=_('Role type'))
    permissions = models.ManyToManyField('auth.Permission', verbose_name=_('Permissions'))
    is_build_in = models.BooleanField(default=False, verbose_name=_('Is build in'))

    class Meta:
        verbose_name = _('Role')

    def __str__(self):
        return self.name


class RoleNamespaceBinding(models.JMSModel):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))
    role = models.ForeignKey(Role, on_delete=models.PROTECT, verbose_name=_('Role'))
    namespace = models.ForeignKey('namespaces.Namespace', on_delete=models.CASCADE, verbose_name=_('Namespaces'))

    class Meta:
        verbose_name = _('Role Namespace Binding')
        unique_together = [('user', 'role', 'namespace')]


class RoleOrgBinding(models.JMSModel):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))
    role = models.ForeignKey(Role, on_delete=models.PROTECT, verbose_name=_('Role'))
    org = models.ForeignKey('orgs.Organization', on_delete=models.CASCADE, verbose_name=_('Organizations'))

    class Meta:
        verbose_name = _('Role Org Binding')
