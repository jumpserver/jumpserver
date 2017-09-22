from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apply_perms.models import ApplyPermission
from perms.models import AssetPermission
import json
from perms.utils import associate_system_users_and_assets
from assets.models import Asset, AssetGroup, SystemUser
from users.models import UserGroup

@receiver(post_save, sender = ApplyPermission)
def create_asset_permission(sender, instance, created, **kwargs):
    if not created and instance.status == 'Approved':
      user_groups = UserGroup.objects.filter(id__in=json.loads(instance.user_groups))
      assets = Asset.objects.filter(id__in=json.loads(instance.assets))
      asset_groups = AssetGroup.objects.filter(id__in=json.loads(instance.asset_groups))
      system_users = SystemUser.objects.filter(id__in=json.loads(instance.system_users))
      associate_system_users_and_assets(system_users, assets, asset_groups)
      asset_permission = AssetPermission.objects.create(name=instance.name,
                                                        is_active=True,
                                                        created_by=instance.approver.username)
      instance.asset_permission=asset_permission
      instance.save()

      asset_permission.user_groups=user_groups
      asset_permission.assets=assets
      asset_permission.asset_groups=asset_groups
      asset_permission.system_users=system_users
      asset_permission.save()


@receiver(post_delete, sender = ApplyPermission)
def delete_asset_permission(sender, instance, **kwargs):
    pass
