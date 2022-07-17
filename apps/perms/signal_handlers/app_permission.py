import itertools

from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from users.models import User, UserGroup
from assets.models import Asset, SystemUser
from applications.models import Application
from common.utils import get_logger
from common.exceptions import M2MReverseNotAllowed
from common.decorator import on_transaction_commit
from common.const.signals import POST_ADD
from perms.models import ApplicationPermission
from applications.models import Account as AppAccount


logger = get_logger(__file__)


@receiver(m2m_changed, sender=ApplicationPermission.applications.through)
@on_transaction_commit
def on_app_permission_applications_changed(sender, instance, action, reverse, pk_set, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed
    if action != POST_ADD:
        return

    logger.debug("Application permission applications change signal received")
    system_users = instance.system_users.all()
    set_remote_app_asset_system_users_if_need(instance, system_users=system_users)

    apps = Application.objects.filter(pk__in=pk_set)
    set_app_accounts(apps, system_users)


def set_app_accounts(apps, system_users):
    for app, system_user in itertools.product(apps, system_users):
        AppAccount.objects.get_or_create(
            defaults={'app': app, 'systemuser': system_user},
            app=app, systemuser=system_user
        )


def set_remote_app_asset_system_users_if_need(instance: ApplicationPermission, system_users=None,
                                              users=None, groups=None):
    if not instance.category_remote_app:
        return

    attrs = instance.applications.all().values_list('attrs', flat=True)
    asset_ids = [attr['asset'] for attr in attrs if attr.get('asset')]
    # 远程应用中资产可能在资产表里不存在
    asset_ids = Asset.objects.filter(id__in=asset_ids).values_list('id', flat=True)
    if not asset_ids:
        return

    system_users = system_users or instance.system_users.all()
    for system_user in system_users:
        system_user.add_related_assets(asset_ids)

        if system_user.username_same_with_user:
            users = users or instance.users.all()
            groups = groups or instance.user_groups.all()
            system_user.groups.add(*groups)
            system_user.users.add(*users)


@receiver(m2m_changed, sender=ApplicationPermission.system_users.through)
@on_transaction_commit
def on_app_permission_system_users_changed(sender, instance, action, reverse, pk_set, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed
    if action != POST_ADD:
        return

    logger.debug("Application permission system_users change signal received")
    system_users = SystemUser.objects.filter(pk__in=pk_set)

    set_remote_app_asset_system_users_if_need(instance, system_users=system_users)
    apps = instance.applications.all()
    set_app_accounts(apps, system_users)


@receiver(m2m_changed, sender=ApplicationPermission.users.through)
@on_transaction_commit
def on_app_permission_users_changed(sender, instance, action, reverse, pk_set, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed
    if action != POST_ADD:
        return

    logger.debug("Application permission users change signal received")
    users = User.objects.filter(pk__in=pk_set)
    set_remote_app_asset_system_users_if_need(instance, users=users)


@receiver(m2m_changed, sender=ApplicationPermission.user_groups.through)
@on_transaction_commit
def on_app_permission_user_groups_changed(sender, instance, action, reverse, pk_set, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed
    if action != POST_ADD:
        return

    logger.debug("Application permission user groups change signal received")
    groups = UserGroup.objects.filter(pk__in=pk_set)
    set_remote_app_asset_system_users_if_need(instance, groups=groups)
