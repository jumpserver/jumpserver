import json
import re
from collections import defaultdict, deque
from uuid import UUID

from .conditions import validate_condition
from .errors import WorkflowConfigurationError

RESOLVERS = {'user', 'user_group', 'role', 'org_admin', 'applicant_manager', 'asset_owner'}


def json_snapshot(value, max_bytes=262144):
    try:
        encoded = json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        raise WorkflowConfigurationError('Workflow data must contain only finite JSON values.')
    if len(encoded.encode()) > max_bytes:
        raise WorkflowConfigurationError('Workflow data exceeds the size limit.')
    return json.loads(encoded)


def validate_approvers(spec):
    if not isinstance(spec, dict) or not isinstance(spec.get('type'), str) or spec['type'] not in RESOLVERS:
        raise WorkflowConfigurationError('Unknown approver resolver.')
    if spec.keys() - {'type', 'value'}:
        raise WorkflowConfigurationError('Unknown approver configuration field.')
    if spec['type'] in ('user', 'user_group', 'role'):
        ids = spec.get('value')
        if isinstance(ids, str):
            ids = [ids]
        if not isinstance(ids, list) or not 1 <= len(ids) <= 1000:
            raise WorkflowConfigurationError('Approvers require between 1 and 1000 resource IDs.')
        try:
            for value in ids:
                UUID(value)
        except (ValueError, TypeError, AttributeError):
            raise WorkflowConfigurationError('Approver resource IDs must be UUIDs.')
        spec['value'] = list(dict.fromkeys(str(UUID(value)) for value in ids))
    elif 'value' in spec:
        raise WorkflowConfigurationError('This resolver reads IDs from the request snapshot or organization.')


def validate_approval(config):
    if config.keys() - {'approvers', 'strategy', 'required', 'allow_transfer', 'allow_add_approver', 'timeout', 'timeout_action', 'exclude_applicant'}:
        raise WorkflowConfigurationError('Unknown approval configuration field.')
    validate_approvers(config.get('approvers'))
    strategy = config.setdefault('strategy', 'any')
    if strategy not in ('any', 'all', 'quorum'):
        raise WorkflowConfigurationError('Approval strategy must be any, all or quorum.')
    if strategy == 'quorum':
        if type(config.get('required')) is not int or not 1 <= config['required'] <= 1000:
            raise WorkflowConfigurationError('Quorum requires a positive approval count up to 1000.')
    elif 'required' in config:
        raise WorkflowConfigurationError('Only quorum accepts a required approval count.')
    for key, default in [('allow_transfer', False), ('allow_add_approver', False), ('exclude_applicant', True)]:
        if type(config.setdefault(key, default)) is not bool:
            raise WorkflowConfigurationError(f'{key} must be a boolean.')
    timeout = config.setdefault('timeout', 0)
    if type(timeout) is not int or not 0 <= timeout <= 31536000:
        raise WorkflowConfigurationError('Timeout must be seconds between 0 and 31536000.')
    if config.setdefault('timeout_action', 'expire') not in ('expire', 'reject'):
        raise WorkflowConfigurationError('Timeout action must be expire or reject.')


def validate_cc(config):
    if set(config) != {'users'} or not isinstance(config['users'], list) or not 1 <= len(config['users']) <= 1000:
        raise WorkflowConfigurationError('A CC node requires between 1 and 1000 user IDs.')
    try:
        config['users'] = list(dict.fromkeys(str(UUID(value)) for value in config['users']))
    except (ValueError, TypeError, AttributeError):
        raise WorkflowConfigurationError('CC user IDs must be UUIDs.')


def validate_definition(definition):
    """Return a canonical, bounded, exclusive-branch DAG; never execute source code."""
    definition = json_snapshot(definition)
    if not isinstance(definition, dict) or set(definition) != {'nodes', 'edges'}:
        raise WorkflowConfigurationError('A workflow requires nodes and edges.')
    nodes, edges = definition['nodes'], definition['edges']
    if not isinstance(nodes, list) or not 2 <= len(nodes) <= 128:
        raise WorkflowConfigurationError('A workflow requires between 2 and 128 nodes.')
    if not isinstance(edges, list) or len(edges) > 256:
        raise WorkflowConfigurationError('A workflow supports at most 256 edges.')
    by_id = {}
    for node in nodes:
        if not isinstance(node, dict) or node.keys() - {'id', 'type', 'name', 'config', 'position'}:
            raise WorkflowConfigurationError('Invalid workflow node.')
        key, kind = node.get('id'), node.get('type')
        if not isinstance(key, str) or not re.fullmatch(r'[\w-]{1,64}', key) or key in by_id:
            raise WorkflowConfigurationError('Node IDs must be unique strings of up to 64 letters, digits, underscores or hyphens.')
        if kind not in ('start', 'approval', 'condition', 'cc', 'end'):
            raise WorkflowConfigurationError('Unsupported node type.')
        node.setdefault('name', key)
        if not isinstance(node['name'], str) or len(node['name']) > 128:
            raise WorkflowConfigurationError('Node names must be strings of up to 128 characters.')
        config = node.setdefault('config', {})
        if not isinstance(config, dict):
            raise WorkflowConfigurationError('Node config must be an object.')
        if kind == 'approval':
            validate_approval(config)
        elif kind == 'condition':
            validate_condition(config)
        elif kind == 'cc':
            validate_cc(config)
        elif config:
            raise WorkflowConfigurationError('Start and end nodes do not accept configuration.')
        position = node.setdefault('position', {'x': 0, 'y': 0})
        if not isinstance(position, dict) or set(position) != {'x', 'y'} or any(
            type(v) is not int or abs(v) > 1000000 for v in position.values()
        ):
            raise WorkflowConfigurationError('Positions require bounded integer x and y coordinates.')
        by_id[key] = node
    starts = [n['id'] for n in nodes if n['type'] == 'start']
    ends = [n['id'] for n in nodes if n['type'] == 'end']
    if len(starts) != 1 or len(ends) != 1:
        raise WorkflowConfigurationError('A workflow requires exactly one start and one end.')
    incoming, outgoing, pairs, normalized = defaultdict(list), defaultdict(list), set(), []
    for edge in edges:
        if isinstance(edge, list) and len(edge) == 2 and all(isinstance(v, str) for v in edge):
            source, target = edge
            condition = None
            if ':' in source:
                source, branch = source.rsplit(':', 1)
                if branch not in ('true', 'false'):
                    raise WorkflowConfigurationError('Branch suffix must be true or false.')
                condition = branch == 'true'
            edge = {'source': source, 'target': target, 'condition': condition}
        if not isinstance(edge, dict) or edge.keys() - {'source', 'target', 'condition', 'priority'}:
            raise WorkflowConfigurationError('Invalid workflow edge.')
        source, target = edge.get('source'), edge.get('target')
        if not isinstance(source, str) or not isinstance(target, str) or source not in by_id or target not in by_id:
            raise WorkflowConfigurationError('Edges must reference existing nodes.')
        if source == target or (source, target) in pairs:
            raise WorkflowConfigurationError('Duplicate edges and self loops are not allowed.')
        edge.setdefault('condition', None)
        edge.setdefault('priority', 0)
        if edge['condition'] is not None and type(edge['condition']) is not bool:
            raise WorkflowConfigurationError('Branch conditions must be booleans.')
        if type(edge['priority']) is not int or not 0 <= edge['priority'] <= 1000000:
            raise WorkflowConfigurationError('Edge priority must be a nonnegative bounded integer.')
        incoming[target].append(edge)
        outgoing[source].append(edge)
        pairs.add((source, target))
        normalized.append(edge)
    for key, node in by_id.items():
        ins, outs, kind = incoming[key], outgoing[key], node['type']
        if kind == 'start' and ins or kind != 'start' and not ins:
            raise WorkflowConfigurationError('Only the start node may have no incoming edges.')
        if kind == 'condition':
            if len(outs) != 2 or {e['condition'] for e in outs} != {True, False}:
                raise WorkflowConfigurationError('Conditions require one true and one false branch.')
        elif len(outs) != (0 if kind == 'end' else 1) or any(e['condition'] is not None for e in outs):
            raise WorkflowConfigurationError('Only condition nodes can branch; end nodes cannot have outgoing edges.')
    # Kahn's algorithm also rejects disconnected cycles. A unique source and sink
    # with these degree rules guarantee every node is reachable and can finish.
    indegrees = {key: len(incoming[key]) for key in by_id}
    queue, visited = deque(starts), 0
    while queue:
        key = queue.popleft()
        visited += 1
        for edge in outgoing[key]:
            indegrees[edge['target']] -= 1
            if indegrees[edge['target']] == 0:
                queue.append(edge['target'])
    if visited != len(nodes):
        raise WorkflowConfigurationError('Workflows must be acyclic and fully reachable.')
    definition['edges'] = normalized
    return definition
