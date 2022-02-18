from django.dispatch import receiver
from django.db.models.signals import post_migrate
from django.apps import apps

from .builtin import BuiltinRole


@receiver(post_migrate)
def after_migrate_update_builtin_role_permissions(sender, app_config, **kwargs):
    # 最后一个 app migrations 后执行, 更新内置角色的权限
    last_app = list(apps.get_app_configs())[-1]
    if app_config.name == last_app.name:
        print("After migration, update builtin role permissions")
        BuiltinRole.sync_to_db()
