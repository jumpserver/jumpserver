from chat_ai.executor.sanitizer import summarize


TIMELINE_MARKERS = ('session', 'command', 'audit', 'login_log', 'operate_log', 'job_log')
METRIC_MARKERS = ('metric', 'status')
ASSET_LIST_OPERATIONS = {
    'assets_assets_list',
    'assets_hosts_list',
    'assets_nodes_assets_list',
}
ASSET_LIST_COLUMNS = (
    'name',
    'address',
    'platform',
    'accounts_amount',
    'is_active',
    'date_verified',
)


def _scalar(value):
    return value is None or isinstance(value, (str, int, float, bool))


def _rows(value):
    if isinstance(value, dict) and isinstance(value.get('results'), list):
        return value['results']
    if isinstance(value, list):
        return value
    return []


def _display_value(value):
    if isinstance(value, dict):
        for key in ('name', 'label', 'display_name', 'value'):
            if _scalar(value.get(key)) and value.get(key) not in (None, ''):
                return value[key]
    return value


def _table(rows, preferred_columns=()):
    dict_rows = [row for row in rows if isinstance(row, dict)][:20]
    if not dict_rows:
        return {'columns': [], 'rows': []}
    if preferred_columns:
        columns = [
            key for key in preferred_columns
            if any(
                _scalar(_display_value(row.get(key)))
                and _display_value(row.get(key)) not in (None, '')
                for row in dict_rows
            )
        ]
    else:
        columns = []
        for row in dict_rows:
            for key, value in row.items():
                if key not in columns and _scalar(value):
                    columns.append(key)
                if len(columns) >= 10:
                    break
            if len(columns) >= 10:
                break

    table_rows = []
    for index, row in enumerate(dict_rows):
        item = {
            column: _display_value(row.get(column))
            for column in columns
        }
        item['_key'] = row.get('id') or row.get('pk') or index
        table_rows.append(item)
    return {
        'columns': columns,
        'rows': table_rows,
    }


def build_result_card(operation, result):
    data = summarize(result.get('data'))
    rows = _rows(data)
    operation_id = operation.operation_id
    if rows:
        kind = 'timeline' if any(marker in operation_id for marker in TIMELINE_MARKERS) else 'table'
        if operation_id in ASSET_LIST_OPERATIONS:
            content = _table(rows, ASSET_LIST_COLUMNS)
            content['variant'] = 'assets'
        else:
            content = _table(rows)
        if isinstance(data, dict) and isinstance(data.get('count'), int):
            content['total'] = data['count']
    elif any(marker in operation_id for marker in METRIC_MARKERS):
        kind = 'metric'
        content = data
    else:
        kind = 'detail'
        content = data
    title = 'Assets' if operation_id in ASSET_LIST_OPERATIONS else operation.summary or operation_id
    return {
        'type': kind,
        'title': title,
        'source': {
            'type': 'core_api',
            'operation_id': operation_id,
            'method': operation.method,
            'path': operation.path,
            'status_code': result.get('status_code', 0),
        },
        'content': content,
    }


def build_source_card(query, provider, sources):
    return {
        'type': 'sources',
        'title': query,
        'source': {'type': 'web_search', 'provider': provider},
        'content': {'sources': summarize(sources)},
    }
