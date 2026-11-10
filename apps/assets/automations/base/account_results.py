"""Whitelisted account identities and outcomes from the current execution."""
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


def execution_account_results(result):
    result = result or {}
    outcomes = {str(target): ('success', '') for target in result.get('ok_assets', [])}
    for target, error in result.get('fail_assets', []):
        outcomes[str(target)] = ('failed', str(error))

    accounts = result.get('account_details', {})
    assets = result.get('asset_details', {})
    rows = []
    for target, (status, error) in outcomes.items():
        identity = {**assets.get(target, {}), **accounts.get(target, {})}
        if not identity:
            continue
        row = {key: str(identity.get(key) or '') for key in SAFE_FIELDS}
        row.update({
            'id': target, 'status': status, 'error': error,
            'privileged': identity.get('privileged') if isinstance(identity.get('privileged'), bool) else None,
        })
        rows.append(row)
    return rows
