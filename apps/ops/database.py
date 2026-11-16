"""Database job capabilities shared by inventory, policy and runner selection."""

DATABASE_JOB_MODULES = ('mysql', 'mariadb', 'postgresql', 'sqlserver', 'oracle',
                        'dameng', 'oceanbase', 'db2', 'clickhouse')
NATIVE_DATABASE_JOB_MODULES = ('oracle', 'dameng', 'oceanbase', 'db2', 'clickhouse')
DATABASE_JOB_PROTOCOLS = frozenset(DATABASE_JOB_MODULES) - {'oceanbase'}


def database_module_matches(module, asset_type, protocol, options=None):
    options = options or {}
    if module == 'oceanbase':
        return asset_type == 'oceanbase' and protocol == 'mysql'
    if asset_type == 'oceanbase' and options.get('tenant_mode', 'mysql') == 'oracle':
        return False
    if module in ('mysql', 'mariadb'):
        return protocol in ('mysql', 'mariadb')
    return module in DATABASE_JOB_MODULES and module == protocol
