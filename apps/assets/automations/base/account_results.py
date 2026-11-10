"""Display-only account identities and per-execution connectivity outcomes."""
import re
from collections import Counter

ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
TARGET = re.compile(
    r'^(?P<name>.*)__(?P<id>[0-9a-f-]{36})(?:__account_(?P<account_id>[0-9a-f-]{36}))?'
    r'(?:\((?P<username>.*)\))?$', re.I
)
ANNOUNCEMENT = re.compile(
    r'• (?P<target>.+?)(?:: processing; execution account: |：正在处理，执行账号：)(?P<account>.+)$'
)
IDENTITY = re.compile(
    r'^(?P<name>.*?)\s*[（(](?:username: |用户名：)(?P<username>.*?)'
    r'(?:, privileged: |，特权账号：)(?P<privileged>Yes|No|是|否)[）)](?:\s.*)?$'
)
LABEL = re.compile(r'^(?P<name>.+)\[(?P<address>[^\[\]]*)\] / (?P<username>.*)$')
SAFE_FIELDS = ('asset_id', 'asset_name', 'asset_address', 'account_id', 'name', 'username')


def account_snapshot(detail, execution_type):
    """Never persist credentials or authentication configuration from inventory."""
    asset = detail.get('jms_asset') or {}
    account = detail.get('account' if execution_type == 'verify_account' else 'jms_account') or {}
    username = account.get('full_username') or account.get('username')
    if not asset.get('id') or not username:
        return None
    return {
        'asset_id': str(asset['id']),
        'asset_name': str(asset.get('name', '')),
        'asset_address': str(asset.get('origin_address') or asset.get('address', '')),
        'account_id': str(account.get('id') or ''),
        'name': str(account.get('name') or ''),
        'username': str(username),
        'privileged': account.get('privileged') if isinstance(account.get('privileged'), bool) else None,
    }


def legacy_ping_accounts(lines):
    identities = []
    for line in lines:
        match = ANNOUNCEMENT.search(ANSI.sub('', line).strip())
        if not match:
            continue
        label = LABEL.fullmatch(match['target'])
        account = IDENTITY.fullmatch(match['account'])
        if not label or not account or label['username'] != account['username']:
            continue
        identity = {
            'asset_name': label['name'], 'asset_address': label['address'],
            'name': account['name'], 'username': account['username'],
            'privileged': account['privileged'] in ('Yes', '是'),
        }
        if identity not in identities:
            identities.append(identity)
    return identities


def execution_account_results(result, execution_type, log_lines=()):
    result = result or {}
    outcomes = {}
    for target in result.get('ok_assets', []):
        outcomes[str(target)] = ('success', '')
    for target, error in result.get('fail_assets', []):
        outcomes[str(target)] = ('failed', str(error))
    details = result.get('account_details', {})
    assets = result.get('asset_details', {})
    legacy = legacy_ping_accounts(log_lines) if execution_type == 'ping' and not details else []
    name_counts = Counter(
        match['name'] for target in outcomes if (match := TARGET.fullmatch(target))
    )
    rows, unresolved = [], 0
    for target, (status, error) in outcomes.items():
        identity = details.get(target)
        match = TARGET.fullmatch(target)
        if not identity and match and 'account_details' not in result:
            asset = assets.get(target, {})
            if execution_type == 'verify_account' and match['username']:
                # The target names identify the verified account, NOT the privileged
                # login account in the legacy "execution account" log message.
                identity = {
                    **asset, 'asset_id': match['id'],
                    'asset_name': asset.get('asset_name') or match['name'],
                    'account_id': match['account_id'],
                    'username': match['username'], 'privileged': None,
                }
            elif execution_type == 'ping':
                candidates = [item for item in legacy if
                    re.sub(r'[ \[\]/]', '_', item['asset_name']) == match['name']
                    and (not asset.get('asset_address') or item['asset_address'] == asset['asset_address'])
                ]
                if len(candidates) == 1 and (name_counts[match['name']] == 1 or asset.get('asset_address')):
                    identity = {**candidates[0], 'asset_id': match['id']}
        if not identity or not identity.get('username'):
            unresolved += 1
            continue
        row = {key: str(identity.get(key) or '') for key in SAFE_FIELDS}
        row.update({
            'id': target, 'status': status, 'error': error,
            'privileged': identity.get('privileged') if isinstance(identity.get('privileged'), bool) else None,
        })
        rows.append(row)
    return {'rows': rows, 'unresolved': unresolved}


def get_execution_account_results(execution):
    result = execution.result or {}
    if execution.type != 'ping' or 'account_details' in result:
        return execution_account_results(result, execution.type)
    from django.conf import settings
    from ops.utils import get_task_log_path
    path = get_task_log_path(settings.CELERY_LOG_DIR, execution.id, create=False)
    try:
        with open(path, encoding='utf-8', errors='replace') as log:
            # Stream the log, retaining only whitelisted identity fields.
            return execution_account_results(result, execution.type, log)
    except OSError:
        return execution_account_results(result, execution.type)
