from collections import defaultdict

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from assets.models import Asset
from common.decorator import on_transaction_commit
from common.utils import get_logger
from .models import Account, PushAccountAutomation
from .utils import SecretGenerator

logger = get_logger(__name__)


@receiver(pre_save, sender=Account)
def on_account_pre_create(sender, instance, **kwargs):
    # 升级版本号
    instance.version += 1
    # 即使在 root 组织也不怕
    instance.org_id = instance.asset.org_id


@receiver(post_save, sender=Asset)
@on_transaction_commit
def on_asset_create(sender, instance, created=False, **kwargs):
    from .serializers import TriggerChoice
    from perms.utils import AssetPermissionUtil

    if not created:
        return

    automations = PushAccountAutomation.objects.filter(
        triggers__contains=TriggerChoice.on_asset_create
    )
    account_automation_map = {auto.username: auto for auto in automations}

    util = AssetPermissionUtil()
    permissions = util.get_permissions_for_assets([instance], with_node=True)
    account_permission_map = defaultdict(list)
    for permission in permissions:
        for account in permission.accounts:
            account_permission_map[account].append(permission)

    username_automation_map = {}
    for username, automation in account_automation_map.items():
        if username != '@USER':
            username_automation_map[username] = automation
            continue

        asset_permissions = account_permission_map.get(username)
        if not asset_permissions:
            continue
        asset_permissions = util.get_permissions([p.id for p in asset_permissions])
        usernames = asset_permissions.values_list('users__username', flat=True).distinct()
        for _username in usernames:
            username_automation_map[_username] = automation

    asset_usernames_exists = instance.accounts.values_list('username', flat=True)
    accounts_to_create = []
    accounts_to_push = []
    for username, automation in username_automation_map.items():
        if username in asset_usernames_exists:
            continue

        if automation.secret_strategy != 'specific':
            secret_generator = SecretGenerator(
                automation.secret_strategy, automation.secret_type,
                automation.password_rules
            )
            secret = secret_generator.get_secret()
        else:
            secret = automation.secret

        account = Account(
            username=username, secret=secret,
            asset=instance, secret_type=automation.secret_type,
            comment='Create by account creation {}'.format(automation.name),
        )
        accounts_to_create.append(account)
        if automation.action == 'create_and_push':
            accounts_to_push.append(account)

        logger.debug(f'Create account {account} for asset {instance}')
