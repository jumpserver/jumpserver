from chat_ai.executor.sanitizer import summarize


TIMELINE_MARKERS = ('session', 'command', 'audit', 'login_log', 'operate_log', 'job_log')
METRIC_MARKERS = ('metric', 'status')


def _scalar(value):
    return value is None or isinstance(value, (str, int, float, bool))


def _rows(value):
    if isinstance(value, dict) and isinstance(value.get('results'), list):
        return value['results']
    if isinstance(value, list):
        return value
    return []


def _table(rows):
    dict_rows = [row for row in rows if isinstance(row, dict)][:20]
    if not dict_rows:
        return {'columns': [], 'rows': []}
    columns = []
    for row in dict_rows:
        for key, value in row.items():
            if key not in columns and _scalar(value):
                columns.append(key)
            if len(columns) >= 10:
                break
        if len(columns) >= 10:
            break
    return {
        'columns': columns,
        'rows': [
            {column: row.get(column) for column in columns}
            for row in dict_rows
        ],
    }


def build_result_card(operation, result):
    data = summarize(result.get('data'))
    rows = _rows(data)
    operation_id = operation.operation_id
    if rows:
        kind = 'timeline' if any(marker in operation_id for marker in TIMELINE_MARKERS) else 'table'
        content = _table(rows)
        if isinstance(data, dict) and isinstance(data.get('count'), int):
            content['total'] = data['count']
    elif any(marker in operation_id for marker in METRIC_MARKERS):
        kind = 'metric'
        content = data
    else:
        kind = 'detail'
        content = data
    return {
        'type': kind,
        'title': operation.summary or operation_id,
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
