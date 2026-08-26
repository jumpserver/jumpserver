import re


QUERY_ALIASES = {
    '创建': ('create', 'add', 'new'),
    '新增': ('create', 'add'),
    '查询': ('list', 'retrieve', 'search', 'get'),
    '搜索': ('search', 'list'),
    '主机': ('host', 'asset'),
    '资产': ('asset', 'host'),
    '节点': ('node',),
    '平台': ('platform',),
    '用户': ('user',),
    '会话': ('session',),
    '命令': ('command',),
    '作业': ('job',),
    '审计': ('audit', 'log'),
    '生产环境': ('production', 'environment'),
    '状态': ('status', 'health'),
}


def tokenize(value):
    value = (value or '').lower()
    latin_groups = re.findall(r'[a-z0-9_\-/]+', value)
    latin = list(latin_groups)
    for group in latin_groups:
        latin.extend(item for item in re.split(r'[_\-/]+', group) if item)
    latin.extend(item[:-1] for item in list(latin) if len(item) > 3 and item.endswith('s'))
    cjk = ''.join(re.findall(r'[\u4e00-\u9fff]', value))
    cjk_tokens = list(cjk) + [cjk[i:i + 2] for i in range(max(0, len(cjk) - 1))]
    aliases = []
    for source, targets in QUERY_ALIASES.items():
        if source in value:
            aliases.extend(targets)
    return set(latin + cjk_tokens + aliases)


class OperationSearch:
    FIELD_WEIGHTS = {
        'operation_id': 8,
        'summary': 7,
        'tags': 5,
        'path': 4,
        'description': 2,
        'method': 1,
    }

    def __init__(self, registry, policy=None):
        self.registry = registry
        self.policy = policy

    def _score(self, operation, query, query_tokens):
        score = 0
        values = {
            'operation_id': operation.operation_id,
            'summary': operation.summary,
            'tags': ' '.join(operation.tags),
            'path': operation.path,
            'description': operation.description,
            'method': operation.method,
        }
        for field, value in values.items():
            value_tokens = tokenize(value)
            score += len(query_tokens & value_tokens) * self.FIELD_WEIGHTS[field]
            if query and query.lower() in (value or '').lower():
                score += self.FIELD_WEIGHTS[field] * 2
        return score

    def search(self, query, limit=5):
        query_tokens = tokenize(query)
        ranked = []
        for operation in self.registry.operations.values():
            if self.policy and not self.policy.is_searchable(operation):
                continue
            score = self._score(operation, query, query_tokens)
            if score > 0:
                ranked.append((score, operation.operation_id, operation))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [operation for _, _, operation in ranked[:limit]]
