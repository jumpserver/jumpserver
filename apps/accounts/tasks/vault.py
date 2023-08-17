from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from celery import shared_task
from django.utils.translation import gettext_lazy as _

from accounts.backends import vault_client
from accounts.models import Account, AccountTemplate
from common.utils import get_logger
from orgs.utils import tmp_to_root_org

logger = get_logger(__name__)


def sync_instance(instance):
    instance_desc = f'[{instance._meta.verbose_name}-{instance.id}-{instance}]'
    if instance.secret_has_save_to_vault:
        msg = f'\033[32m- 跳过同步: {instance_desc}, 原因: [已同步]'
        return "skipped", msg

    try:
        vault_client.create(instance)
    except Exception as e:
        msg = f'\033[31m- 同步失败: {instance_desc}, 原因: [{e}]'
        return "failed", msg
    else:
        msg = f'\033[32m- 同步成功: {instance_desc}'
        return "succeeded", msg


@shared_task(verbose_name=_('Sync secret to vault'))
def sync_secret_to_vault():
    if not vault_client.enabled:
        # 这里不能判断 settings.VAULT_ENABLED, 必须判断当前 vault_client 的类型
        print('\033[35m>>> 当前 Vault 功能未开启, 不需要同步')
        return

    failed, skipped, succeeded = 0, 0, 0
    to_sync_models = [Account, AccountTemplate, Account.history.model]
    print(f'\033[33m>>> 开始同步密钥数据到 Vault ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})')
    with tmp_to_root_org():
        instances = []
        for model in to_sync_models:
            instances += list(model.objects.all())

        with ThreadPoolExecutor(max_workers=10) as executor:
            tasks = [executor.submit(sync_instance, instance) for instance in instances]

            for future in as_completed(tasks):
                status, msg = future.result()
                print(msg)
                if status == "succeeded":
                    succeeded += 1
                elif status == "failed":
                    failed += 1
                elif status == "skipped":
                    skipped += 1

    total = succeeded + failed + skipped
    print(
        f'\033[33m>>> 同步完成: {model.__module__}, '
        f'共计: {total}, '
        f'成功: {succeeded}, '
        f'失败: {failed}, '
        f'跳过: {skipped}'
    )
    print(f'\033[33m>>> 全部同步完成 ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})')
    print('\033[0m')
