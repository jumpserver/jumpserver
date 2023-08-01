import datetime

from celery import shared_task
from django.utils.translation import gettext_lazy as _

from accounts.backends import vault_client
from accounts.models import Account, AccountTemplate
from common.utils import get_logger
from orgs.utils import tmp_to_root_org
from ..const import VaultTypeChoices

logger = get_logger(__name__)


@shared_task(verbose_name=_('Sync secret to vault'))
def sync_secret_to_vault():
    if vault_client.is_type(VaultTypeChoices.local):
        # 这里不能判断 settings.VAULT_TYPE, 必须判断当前 vault_client 的类型
        print('\033[35m>>> 当前 Vault 类型为本地数据库, 不需要同步')
        return

    print('\033[33m>>> 开始同步密钥数据到 Vault ({})'.format(datetime.datetime.now()))
    with tmp_to_root_org():
        to_sync_models = [Account, AccountTemplate, Account.history.model]
        for model in to_sync_models:
            print(f'\033[33m>>> 开始同步: {model.__module__}')
            succeeded = []
            failed = []
            skipped = []
            instances = model.objects.all()
            for instance in instances:
                instance_desc = f'[{instance}]'
                if instance.secret_has_save_to_vault:
                    print(f'\033[32m- 跳过同步: {instance_desc}, 原因: [已同步]')
                    skipped.append(instance)
                    continue
                try:
                    vault_client.create(instance)
                except Exception as e:
                    failed.append(instance)
                    print(f'\033[31m- 同步失败: {instance_desc}, 原因: [{e}]')
                else:
                    succeeded.append(instance)
                    print(f'\033[32m- 同步成功: {instance_desc}')

            total = len(succeeded) + len(failed) + len(skipped)
            print(
                f'\033[33m>>> 同步完成: {model.__module__}, '
                f'共计: {total}, '
                f'成功: {len(succeeded)}, '
                f'失败: {len(failed)}, '
                f'跳过: {len(skipped)}'
            )

    print('\033[33m>>> 全部同步完成 ({})'.format(datetime.datetime.now()))
    print('\033[0m')
