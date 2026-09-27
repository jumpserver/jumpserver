"""Approval requirements specific to delegated asset access."""


def supports_delegated_request(version):
    """Every possible path must pass an organization administrator approval."""
    if not version or not version.published_at:
        return False
    definition = version.as_definition()
    nodes = {node['id']: node for node in definition['nodes']}
    next_nodes = {key: [] for key in nodes}
    for edge in definition['edges']:
        next_nodes[edge['source']].append(edge['target'])
    start = next((key for key, node in nodes.items() if node['type'] == 'start'), None)
    if start is None:
        return False
    pending = [(start, False)]
    seen = set()
    while pending:
        key, has_admin = pending.pop()
        if (key, has_admin) in seen:
            continue
        seen.add((key, has_admin))
        node = nodes[key]
        has_admin |= (node['type'] == 'approval' and
                      node['config'].get('approvers', {}).get('type') == 'org_admin')
        if node['type'] == 'end' and not has_admin:
            return False
        pending.extend((target, has_admin) for target in next_nodes[key])
    return True
