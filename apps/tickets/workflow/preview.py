from graphlib import TopologicalSorter

from tickets.models import WorkflowNodeInstance
from .approvers import resolve_approvers, user_snapshot
from .errors import WorkflowConfigurationError


def upcoming_nodes(instance):
    """Preview the remaining graph and approvers without entering nodes."""
    if instance.state != 'running':
        return []
    visited = set()
    current = None
    for run in instance.node_instances.all():
        # Resource adjustments can restart the same published graph.
        if run.node.type == 'start':
            visited.clear()
        visited.add(run.node_id)
        if run.state == 'running':
            current = run.node_id
    if current is None:
        return []

    nodes = {node.pk: node for node in sorted(instance.version.nodes.all(), key=lambda node: node.key)}
    predecessors = {key: [] for key in nodes}
    successors = {key: [] for key in nodes}
    for edge in instance.version.edges.all():
        predecessors[edge.target_id].append(edge.source_id)
        successors[edge.source_id].append(edge.target_id)
    order = list(TopologicalSorter(predecessors).static_order())
    possible, certain = {}, {}
    for key in reversed(order):
        targets = successors[key]
        possible[key] = {key}.union(*(possible[target] for target in targets))
        # A shared node after both branches is still on every possible route.
        common = set.intersection(*(certain[target] for target in targets)) if targets else set()
        certain[key] = {key} | common

    preview = []
    for key in order:
        if key in visited:
            continue
        node = nodes[key]
        state = 'not_started' if key in certain[current] else (
            'branch_pending' if key in possible[current] else 'skipped'
        )
        item = {
            'id': f'preview-{node.pk}', 'key': node.key, 'type': node.type,
            'name': str(instance.version.workflow.node_display_name(node)),
            'config': node.config, 'state': state, 'required': node.config.get('required', 1),
        }
        if node.type == 'approval' and state != 'skipped':
            run = WorkflowNodeInstance(instance=instance, node=node)
            try:
                users = resolve_approvers(
                    run, instance.context, instance.org_id, instance.applicant_id,
                )
            except WorkflowConfigurationError:
                # Unavailable future approvers must not prevent reading the current task.
                users = []
            item['approvers'] = [user_snapshot(user) for user in users]
        preview.append(item)
    return preview
