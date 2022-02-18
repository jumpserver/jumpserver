from django.dispatch import receiver
from django.db.models.signals import post_migrate

from .builtin import BuiltinRole


@receiver(post_migrate)
def after_migrate_update_builtin_role_permissions(sender, app_config, **kwargs):
    # FBI WARNING: 为啥是 simple_history, 因为 simple_history 是最后一个 app,
    # 保证在最后一个 app 后执行, 并且不会相互依赖
    if app_config.name == 'simple_history':
        print("After migration, update builtin role permissions")
        BuiltinRole.sync_to_db()
