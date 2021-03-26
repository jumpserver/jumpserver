from django.db import models
from django.utils.translation import ugettext_lazy as _
from common.mixins.models import CommonModelMixin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


__all__ = ['Role', 'RoleTypeChoices']


class RoleTypeChoices(models.TextChoices):
    safe = 'safe', _('Safe')

    # Method for apps models mapping
    @classmethod
    def get_apps_models_mapping_for_safe(cls):
        return {
            'accounts': ['safe', 'account']
        }

    @classmethod
    def get_permissions(cls, tp):
        method_apps_models_mapping_for_tp = f'get_apps_models_mapping_for_{tp}'
        assert hasattr(cls, method_apps_models_mapping_for_tp), (
            f'Method`{method_apps_models_mapping_for_tp}` is not implemented'
        )
        apps_models_mapping = getattr(cls, method_apps_models_mapping_for_tp)()

        apps_labels = list(apps_models_mapping.keys())
        models_names = []
        for _models_names in list(apps_models_mapping.values()):
            models_names.extend(_models_names)

        content_types_ids = ContentType.objects \
            .filter(app_label__in=apps_labels, model__in=models_names) \
            .values_list('id', flat=True)
        permissions = Permission.objects.filter(content_type__in=content_types_ids)
        return permissions


class Role(CommonModelMixin):
    """ 角色: 相当于权限的集合 """
    # 内置角色:
    # - 账号(Safe)管理员: 拥有所有safe相关的权限
    display_name = models.CharField(max_length=256, verbose_name=_('Display name'))
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    # 角色类型: system / org / safe
    type = models.CharField(
        choices=RoleTypeChoices.choices, default=RoleTypeChoices.safe, max_length=128,
        verbose_name=_('Type')
    )
    # 权限项
    permissions = models.ManyToManyField(
        'auth.Permission', null=True, blank=True, verbose_name=_('Permission'),
    )
    is_builtin = models.BooleanField(default=False, verbose_name=_('Built-in'))
    comment = models.TextField(null=True, blank=True, verbose_name=_('Comment'))

    class Meta:
        pass

    def __str__(self):
        return self.name

    def get_permissions_display(self):
        permissions = list(self.permissions.all().values_list('name', flat=True))
        return permissions

    @classmethod
    def initial_builtin_role(cls):
        """ 初始化内建角色 """
        # safe_admin
        safe_admin_role_name = 'safe_admin'
        safe_admin_role_data = {
            'display_name': 'Safe Admin Role',
            'name': safe_admin_role_name,
            'type': RoleTypeChoices.safe,
            'is_builtin': True,
            'comment': 'Safe Admin Role',
            'created_by': 'System',
        }
        permissions = RoleTypeChoices.get_permissions(tp=RoleTypeChoices.safe)
        safe_admin_role, created = cls.objects.get_or_create(
            defaults=safe_admin_role_data, name=safe_admin_role_name,
        )
        print('created: {}, safe_admin_role: {}'.format(created, safe_admin_role))
        safe_admin_role.permissions.set(permissions)
        return safe_admin_role
