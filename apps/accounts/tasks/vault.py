from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from time import monotonic

from celery import shared_task
from django.db import close_old_connections, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.backends import vault_client
from accounts.const import VaultTypeChoices
from accounts.models import Account, AccountTemplate
from accounts.models.mixins.vault import VAULT_SAVED_SECRET_MARK
from common.utils import get_logger
from common.utils.lock import DistributedLock
from orgs.utils import tmp_to_root_org

logger = get_logger(__name__)

VAULT_TRANSFER_LOCK_NAME = 'accounts:vault-secret-transfer'
PROGRESS_INTERVAL = 100
QUERYSET_CHUNK_SIZE = 200

ACTION_SYNC = 'sync'
ACTION_RESTORE = 'restore'

ANSI_RESET = '\033[0m'
ANSI_BOLD = '\033[1m'
ANSI_RED = '\033[31m'
ANSI_GREEN = '\033[32m'
ANSI_YELLOW = '\033[33m'
ANSI_CYAN = '\033[36m'
ANSI_GRAY = '\033[90m'


def _print_log(message=''):
    print(message, flush=True)


def _color(message, color, bold=False):
    prefix = f'{ANSI_BOLD if bold else ""}{color}'
    return f'{prefix}{message}{ANSI_RESET}'


def _status_counts(stats):
    return ' | '.join((
        _color(f"成功 {stats['succeeded']}", ANSI_GREEN, bold=True),
        _color(f"失败 {stats['failed']}", ANSI_RED, bold=True),
        _color(f"跳过 {stats['skipped']}", ANSI_YELLOW),
    ))


def _format_time(value=None):
    value = value or timezone.localtime()
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime('%Y-%m-%d %H:%M:%S')


def _safe_log_value(value, limit=120):
    value = str(value or '').replace('\r', ' ').replace('\n', ' ')
    return value if len(value) <= limit else f'{value[:limit - 3]}...'


def _instance_desc(instance):
    parts = [
        str(instance._meta.verbose_name),
        f'id={instance.pk}',
    ]
    for field in ('name', 'username'):
        value = _safe_log_value(getattr(instance, field, ''))
        if value:
            parts.append(f'{field}={value}')
    return ' | '.join(parts)


def _restore_instance_secret(instance, secret):
    instance.restore_secret_from_vault(secret)


def _get_locked_instance(instance):
    return (
        instance.__class__._base_manager.select_for_update()
        .get(pk=instance.pk)
    )


def _transfer_instance(action, instance):
    """Transfer one secret without leaking its value to the task result or log."""
    close_old_connections()
    try:
        # Serialize each database row with normal account updates. This keeps
        # the local marker and the external secret consistent if an account is
        # edited while a migration task is running.
        with transaction.atomic():
            instance = _get_locked_instance(instance)
            if action == ACTION_SYNC:
                if instance.secret_has_save_to_vault:
                    return 'skipped', _instance_desc(instance), ''
                vault_client.create(instance)
            else:
                if not instance.secret_has_save_to_vault:
                    return 'skipped', _instance_desc(instance), ''
                secret = vault_client.get_for_restore(instance)
                _restore_instance_secret(instance, secret)
            return 'succeeded', _instance_desc(instance), ''
    except Exception as error:
        return 'failed', _instance_desc(instance), _safe_log_value(error, limit=300)
    finally:
        close_old_connections()


def _iter_parallel_results(action, instances, max_workers):
    """Run a bounded number of futures so large installations do not fill memory."""
    iterator = iter(instances)
    max_pending = max(max_workers * 2, 1)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        pending = set()
        for instance in iterator:
            pending.add(executor.submit(_transfer_instance, action, instance))
            if len(pending) >= max_pending:
                break

        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                yield future.result()
                try:
                    instance = next(iterator)
                except StopIteration:
                    continue
                pending.add(executor.submit(_transfer_instance, action, instance))


def _get_model_queryset(model, action):
    queryset = model.objects.all()
    # OpenBao deliberately stores the marker as plaintext, so it can be
    # filtered efficiently. Other backends encrypt it with a random nonce and
    # must inspect the decrypted model value instead.
    if vault_client.type != VaultTypeChoices.openbao:
        return queryset, 0
    if action == ACTION_SYNC:
        queryset = queryset.exclude(_secret=VAULT_SAVED_SECRET_MARK)
    else:
        queryset = queryset.filter(_secret=VAULT_SAVED_SECRET_MARK)
    pending_count = queryset.count()
    return queryset, model.objects.count() - pending_count


def _empty_stats(total=0, skipped=0):
    return {
        'total': total,
        'pending': total - skipped,
        'succeeded': 0,
        'failed': 0,
        'skipped': skipped,
    }


def _print_progress(stats, force=False):
    pre_skipped = stats['total'] - stats['pending']
    processed = (
        stats['succeeded'] + stats['failed'] + stats['skipped'] - pre_skipped
    )
    pending = stats['pending']
    if not force:
        if processed == pending or processed % PROGRESS_INTERVAL:
            return
    percent = 100 if not pending else int(processed * 100 / pending)
    _print_log(
        f"  {_color(f'进度 {processed}/{pending} ({percent:>3}%)', ANSI_CYAN)} | "
        f"{_color(f'成功 {stats['succeeded']}', ANSI_GREEN, bold=True)} | "
        f"{_color(f'失败 {stats['failed']}', ANSI_RED, bold=True)}"
    )


def _transfer_model(model, action, index, model_count, max_workers):
    all_count = model.objects.count()
    queryset, pre_skipped = _get_model_queryset(model, action)
    pending_count = all_count - pre_skipped
    stats = _empty_stats(total=all_count, skipped=pre_skipped)
    model_name = str(model._meta.verbose_name)

    _print_log(_color(f'[{index}/{model_count}] {model_name}', ANSI_CYAN, bold=True))
    _print_log(
        f"  总数 {all_count} | 待检查 {pending_count} | "
        f"{_color(f'预先跳过 {stats['skipped']}', ANSI_YELLOW)}"
    )
    if not pending_count:
        _print_log(_color('  结果 无需处理', ANSI_YELLOW))
        _print_log()
        return stats

    instances = queryset.iterator(chunk_size=QUERYSET_CHUNK_SIZE)
    for status, instance_desc, error in _iter_parallel_results(
            action, instances, max_workers
    ):
        stats[status] += 1
        if status == 'failed':
            _print_log(_color(f'  [失败] {instance_desc} | 原因={error}', ANSI_RED))
        _print_progress(stats)

    _print_progress(stats, force=True)
    _print_log(f"  结果 {_status_counts(stats)}")
    _print_log()
    return stats


def _merge_stats(target, source):
    for key in target:
        target[key] += source[key]


def _print_header(action, max_workers):
    title = '账号密钥同步到 Vault' if action == ACTION_SYNC else '账号密钥还原到本地数据库'
    note = (
        '已存储在 Vault 的数据会自动跳过'
        if action == ACTION_SYNC
        else '仅还原已同步数据，Vault 中的副本不会删除'
    )
    _print_log(_color('=' * 72, ANSI_GRAY))
    _print_log(_color(title, ANSI_CYAN, bold=True))
    _print_log(_color('=' * 72, ANSI_GRAY))
    _print_log(f'{_color("Vault 类型", ANSI_CYAN)} : {vault_client.type}')
    _print_log(f'{_color("开始时间", ANSI_CYAN)}   : {_format_time()}')
    _print_log(f'{_color("并发数", ANSI_CYAN)}     : {max_workers}')
    _print_log(f'{_color("说明", ANSI_CYAN)}       : {note}')
    _print_log(_color('-' * 72, ANSI_GRAY))


def _print_summary(action, stats, started_at):
    action_name = '同步' if action == ACTION_SYNC else '还原'
    duration = monotonic() - started_at
    _print_log(_color('=' * 72, ANSI_GRAY))
    summary_color = ANSI_RED if stats['failed'] else ANSI_GREEN
    _print_log(_color(f'{action_name}完成', summary_color, bold=True))
    _print_log(f"总计 {stats['total']} | {_status_counts(stats)}")
    _print_log(f'结束时间   : {_format_time()}')
    _print_log(f'耗时       : {duration:.2f} 秒')
    _print_log(_color('=' * 72, ANSI_GRAY))


def _preflight(action):
    if not vault_client.enabled:
        _print_log(_color('[无法执行] Vault 功能未开启', ANSI_RED, bold=True))
        return False
    if VaultTypeChoices.local == vault_client.type:
        _print_log(_color(
            '[无法执行] 第三方 Vault 客户端初始化失败，当前使用本地数据库存储',
            ANSI_RED, bold=True
        ))
        return False
    if action not in (ACTION_SYNC, ACTION_RESTORE):
        _print_log(_color(f'[无法执行] 不支持的操作: {action}', ANSI_RED, bold=True))
        return False
    return True


def _run_secret_transfer(action):
    started_at = monotonic()
    if not _preflight(action):
        return {'status': 'failed', 'action': action}

    lock = DistributedLock(VAULT_TRANSFER_LOCK_NAME)
    try:
        acquired = lock.acquire(blocking=False)
    except Exception as error:
        logger.exception('Acquire Vault secret transfer lock failed')
        _print_log(_color(
            f'[无法执行] 获取迁移锁失败: {_safe_log_value(error, limit=300)}',
            ANSI_RED, bold=True
        ))
        return {'status': 'failed', 'action': action}

    if not acquired:
        _print_log(_color(
            '[已跳过] 另一个账号密钥同步或还原任务正在执行',
            ANSI_YELLOW, bold=True
        ))
        return {'status': 'skipped', 'action': action}

    models = (Account, AccountTemplate, Account.history.model)
    max_workers = 1 if VaultTypeChoices.azure == vault_client.type else 10
    summary = _empty_stats()
    try:
        _print_header(action, max_workers)
        with tmp_to_root_org():
            for index, model in enumerate(models, start=1):
                stats = _transfer_model(
                    model, action, index, len(models), max_workers
                )
                _merge_stats(summary, stats)
        _print_summary(action, summary, started_at)
        status = 'failed' if summary['failed'] else 'succeeded'
        return {
            'status': status,
            'action': action,
            'vault_type': vault_client.type,
            'summary': summary,
        }
    finally:
        try:
            lock.release()
        except Exception:
            logger.exception('Release Vault secret transfer lock failed')


@shared_task(
    verbose_name=_('Sync secret to vault'),
    description=_(
        "When clicking 'Sync' in 'System Settings - Features - Account Storage' this task will be executed"
    )
)
def sync_secret_to_vault():
    return _run_secret_transfer(ACTION_SYNC)


@shared_task(
    verbose_name=_('Restore secret from vault'),
    description=_(
        "When clicking 'Restore' in 'System Settings - Features - Account Storage' this task will be executed"
    )
)
def restore_secret_from_vault():
    return _run_secret_transfer(ACTION_RESTORE)
