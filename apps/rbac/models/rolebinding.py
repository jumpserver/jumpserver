from django.utils.translation import gettext_lazy as _
from django.db import models
from django.db.models import Q
from rest_framework.serializers import ValidationError

from common.db.models import JMSModel
from common.utils import lazyproperty
from orgs.utils import current_org
from .role import Role
from ..const import Scope

__all__ = ['RoleBinding', 'SystemRoleBinding', 'OrgRoleBinding']


class RoleBindingManager(models.Manager):
    def get_queryset(self):
        queryset = super(RoleBindingManager, self).get_queryset()
        q = Q(scope=Scope.system)
        if not current_org.is_root():
            q |= Q(org_id=current_org.id, scope=Scope.org)
        queryset = queryset.filter(q)
        return queryset


class RoleBinding(JMSModel):
    Scope = Scope
    """ 定义 用户-角色 关系 """
    scope = models.CharField(
        max_length=128, choices=Scope.choices, default=Scope.system,
        verbose_name=_('Scope')
    )
    user = models.ForeignKey(
        'users.User', related_name='role_bindings', on_delete=models.CASCADE, verbose_name=_('User')
    )
    role = models.ForeignKey(
        Role, related_name='role_bindings', on_delete=models.CASCADE, verbose_name=_('Role')
    )
    org = models.ForeignKey(
        'orgs.Organization', related_name='role_bindings', blank=True, null=True,
        on_delete=models.CASCADE, verbose_name=_('Organization')
    )
    objects = RoleBindingManager()

    class Meta:
        verbose_name = _('Role binding')
        unique_together = [
            ('user', 'role', 'org'),
        ]

    def __str__(self):
        display = '{user} & {role}'.format(user=self.user, role=self.role)
        if self.org:
            display += ' | {org}'.format(org=self.org)
        return display

    def save(self, *args, **kwargs):
        self.scope = self.role.scope
        return super().save(*args, **kwargs)

    @classmethod
    def get_user_perms(cls, user):
        roles = cls.get_user_roles(user)
        return Role.get_roles_perms(roles)

    @classmethod
    def get_role_users(cls, role):
        from users.models import User
        bindings = cls.objects.filter(role=role, scope=role.scope)
        user_ids = bindings.values_list('user', flat=True).distinct()
        return User.objects.filter(id__in=user_ids)

    @classmethod
    def get_user_roles(cls, user):
        bindings = cls.objects.filter(user=user)
        roles_id = bindings.values_list('role', flat=True).distinct()
        return Role.objects.filter(id__in=roles_id)

    @lazyproperty
    def user_display(self):
        return self.user.name

    @lazyproperty
    def role_display(self):
        return self.role.display_name


class OrgRoleBindingManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        if current_org.is_root():
            return queryset.none()

        queryset = queryset.filter(org=current_org.id)
        return queryset


class OrgRoleBinding(RoleBinding):
    objects = OrgRoleBindingManager()

    def save(self, *args, **kwargs):
        self.org_id = current_org.id
        self.scope = Scope.org
        return super().save(*args, **kwargs)

    def delete(self, **kwargs):
        has_other_role = self.__class__.objects \
            .filter(user=self.user, scope=self.scope) \
            .exclude(id=self.id) \
            .exists()
        if not has_other_role:
            error = _('User last role in org, can not be delete, '
                      'you can remove user from org instead')
            raise ValidationError({'error': error})
        return super().delete(**kwargs)

    class Meta:
        proxy = True
        verbose_name = _('Organization role binding')


class SystemRoleBindingManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset().\
            filter(scope=Scope.org)
        return queryset


class SystemRoleBinding(RoleBinding):
    objects = SystemRoleBindingManager()

    class Meta:
        proxy = True
        verbose_name = _('System role binding')

    def save(self, *args, **kwargs):
        self.scope = Scope.system
        return super().save(*args, **kwargs)
