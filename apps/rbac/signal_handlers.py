from django.dispatch import receiver
from django.db.models.signals import post_migrate, post_save, m2m_changed, post_delete
from django.apps import apps

from .models import SystemRole, OrgRole, OrgRoleBinding, SystemRoleBinding
from .builtin import BuiltinRole


@receiver(post_migrate)
def after_migrate_update_builtin_role_permissions(sender, app_config, **kwargs):
    # 最后一个 app migrations 后执行, 更新内置角色的权限
    last_app = list(apps.get_app_configs())[-1]
    if app_config.name == last_app.name:
        print("\nAfter migration, update builtin role permissions")
        BuiltinRole.sync_to_db()


@receiver(post_save, sender=SystemRole)
def on_system_role_update(sender, instance, **kwargs):
    from users.models import User
    User.expire_users_rbac_perms_cache()


@receiver(m2m_changed, sender=SystemRole.permissions.through)
def on_system_role_permission_changed(sender, instance, **kwargs):
    from users.models import User
    User.expire_users_rbac_perms_cache()


@receiver([post_save, post_delete], sender=SystemRoleBinding)
def on_system_role_binding_update(sender, instance, **kwargs):
    from users.models import User
    User.expire_users_rbac_perms_cache()


@receiver(post_save, sender=OrgRole)
def on_org_role_update(sender, instance, **kwargs):
    from users.models import User
    User.expire_users_rbac_perms_cache()


@receiver(m2m_changed, sender=OrgRole.permissions.through)
def on_org_role_permission_changed(sender, instance, action, **kwargs):
    from users.models import User
    User.expire_users_rbac_perms_cache()


@receiver([post_save, post_delete], sender=OrgRoleBinding)
def on_org_role_binding_update(sender, instance, **kwargs):
    from users.models import User
    User.expire_users_rbac_perms_cache()
