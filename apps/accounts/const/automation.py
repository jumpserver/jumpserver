from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.const import Connectivity
from common.db.fields import TreeChoices

DEFAULT_PASSWORD_LENGTH = 30
DEFAULT_PASSWORD_RULES = {
    'length': DEFAULT_PASSWORD_LENGTH,
    'uppercase': True,
    'lowercase': True,
    'digit': True,
    'symbol': True,
}

__all__ = [
    'AutomationTypes', 'SecretStrategy', 'SSHKeyStrategy', 'Connectivity',
    'DEFAULT_PASSWORD_LENGTH', 'DEFAULT_PASSWORD_RULES', 'TriggerChoice',
    'PushAccountActionChoice', 'AccountBackupType'
]


class AutomationTypes(models.TextChoices):
    push_account = 'push_account', _('Push account')
    change_secret = 'change_secret', _('Change secret')
    verify_account = 'verify_account', _('Verify account')
    remove_account = 'remove_account', _('Remove account')
    gather_accounts = 'gather_accounts', _('Gather accounts')
    verify_gateway_account = 'verify_gateway_account', _('Verify gateway account')

    @classmethod
    def get_type_model(cls, tp):
        from accounts.models import (
            PushAccountAutomation, ChangeSecretAutomation,
            VerifyAccountAutomation, GatherAccountsAutomation,
        )
        type_model_dict = {
            cls.push_account: PushAccountAutomation,
            cls.change_secret: ChangeSecretAutomation,
            cls.verify_account: VerifyAccountAutomation,
            cls.gather_accounts: GatherAccountsAutomation,
        }
        return type_model_dict.get(tp)


class SecretStrategy(models.TextChoices):
    custom = 'specific', _('Specific secret')
    random = 'random', _('Random generate')


class SSHKeyStrategy(models.TextChoices):
    add = 'add', _('Append SSH KEY')
    set = 'set', _('Empty and append SSH KEY')
    set_jms = 'set_jms', _('Replace (Replace only keys pushed by JumpServer) ')


class TriggerChoice(models.TextChoices, TreeChoices):
    # 当资产创建时，直接创建账号，如果是动态账号，需要从授权中查询该资产被授权过的用户，已用户用户名为账号，创建
    on_asset_create = 'on_asset_create', _('On asset create')
    # 授权变化包含，用户加入授权，用户组加入授权，资产加入授权，节点加入授权，账号变化
    # 当添加用户到授权时，查询所有同名账号 automation, 把本授权上的用户 (用户组), 创建到本授权的资产(节点)上
    on_perm_add_user = 'on_perm_add_user', _('On perm add user')
    # 当添加用户组到授权时，查询所有同名账号 automation, 把本授权上的用户 (用户组), 创建到本授权的资产(节点)上
    on_perm_add_user_group = 'on_perm_add_user_group', _('On perm add user group')
    # 当添加资产到授权时，查询授权的所有账号 automation, 创建到本授权的资产上
    on_perm_add_asset = 'on_perm_add_asset', _('On perm add asset')
    # 当添加节点到授权时，查询授权的所有账号 automation, 创建到本授权的节点的资产上
    on_perm_add_node = 'on_perm_add_node', _('On perm add node')
    # 当授权的账号变化时，查询授权的所有账号 automation, 创建到本授权的资产(节点)上
    on_perm_add_account = 'on_perm_add_account', _('On perm add account')
    # 当资产添加到节点时，查询节点的授权规则，查询授权的所有账号 automation, 创建到本授权的资产(节点)上
    on_asset_join_node = 'on_asset_join_node', _('On asset join node')
    # 当用户加入到用户组时，查询用户组的授权规则，查询授权的所有账号 automation, 创建到本授权的资产(节点)上
    on_user_join_group = 'on_user_join_group', _('On user join group')

    @classmethod
    def branches(cls):
        # 和用户和用户组相关的都是动态账号
        #
        return [
            cls.on_asset_create,
            (_("On perm change"), [
                cls.on_perm_add_user,
                cls.on_perm_add_user_group,
                cls.on_perm_add_asset,
                cls.on_perm_add_node,
                cls.on_perm_add_account,
            ]),
            (_("Inherit from group or node"), [
                cls.on_asset_join_node,
                cls.on_user_join_group,
            ])
        ]


class PushAccountActionChoice(models.TextChoices):
    create_and_push = 'create_and_push', _('Create and push')
    only_create = 'only_create', _('Only create')


class AccountBackupType(models.TextChoices):
    """Backup type"""
    email = 'email', _('Email')
    # 目前只支持sftp方式
    object_storage = 'object_storage', _('SFTP')
