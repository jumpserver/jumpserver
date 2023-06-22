from celery import shared_task
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from accounts.backends import get_vault_client
from accounts.models import Account, AccountTemplate
from common.utils import get_logger
from orgs.utils import tmp_to_root_org
from ..const import VaultType

logger = get_logger(__name__)


@shared_task(verbose_name=_('Sync account vault data'), )
def sync_account_vault_data():
    if settings.VAULT_TYPE == VaultType.LOCAL:
        print('\033[35m>>> 当前类型为本地数据库，跳过同步逻辑')
        return

    print('\033[33m>>> 开始同步账号密钥数据到 Vault')
    with tmp_to_root_org():
        accounts = Account.objects.exclude(_secret__isnull=True)
        account_templates = AccountTemplate.objects.exclude(_secret__isnull=True)

        for instance in list(accounts) + list(account_templates):
            vault_client = get_vault_client(instance)
            try:
                vault_client.create()
                print(f'\033[32m- {instance} 已同步')
            except Exception as e:
                print(f'\033[31m- {instance} 同步失败，原因：{e}')

    print('\033[33m>>> 同步完成')
    print('\033[0m')
