from django.utils.translation import gettext
from hashlib import sha256

from django.db import transaction

from orgs.utils import tmp_to_org
from tickets.models import Workflow, WorkflowVersion
from .definition import validate_definition
from .errors import WorkflowConfigurationError, WorkflowConflict
from .publication import publish_workflow


def chain_definitions(definitions):
    """Join each exit to the next entry without changing branches or approval rules."""
    definitions = [validate_definition(item) for item in definitions]
    nodes = [{'id': 'start', 'type': 'start'}, {'id': 'end', 'type': 'end'}]
    edges, entries, mappings = [], [], []
    next_entry = 'end'
    for index in range(len(definitions) - 1, -1, -1):
        definition = definitions[index]
        mapping = {node['id']: f'p{index}_{offset}' for offset, node in enumerate(definition['nodes'])}
        start = next(node['id'] for node in definition['nodes'] if node['type'] == 'start')
        end = next(node['id'] for node in definition['nodes'] if node['type'] == 'end')
        mapping[end] = next_entry
        target = next(edge['target'] for edge in definition['edges'] if edge['source'] == start)
        next_entry = mapping[target]
        mappings.insert(0, (mapping, start))
        entries.insert(0, next_entry)
    for definition, (mapping, start) in zip(definitions, mappings):
        nodes.extend({**node, 'id': mapping[node['id']]} for node in definition['nodes']
                     if node['type'] not in ('start', 'end'))
        edges.extend({**edge, 'source': mapping[edge['source']], 'target': mapping[edge['target']]}
                     for edge in definition['edges'] if edge['source'] != start)
    edges.append({'source': 'start', 'target': entries[0] if entries else 'end'})
    return validate_definition({'nodes': nodes, 'edges': edges})


@transaction.atomic
def compose_workflows(workflows, org_id, ticket_type, *, acl_reviewers=None):
    entries, seen = [], set()
    for index, workflow in enumerate(workflows):
        if workflow.pk in seen and not workflow.requires_acl_reviewers:
            continue
        seen.add(workflow.pk)
        entries.append((workflow, (acl_reviewers or {}).get(index, [])))
    workflows = [workflow for workflow, _ in entries]
    if not workflows:
        raise WorkflowConfigurationError(gettext('Configure reviewers or select a workflow on the ACL.'))
    if len(workflows) == 1:
        workflow, reviewers = entries[0]
        return workflow, {key: reviewers for key in workflow.active_version.acl_reviewer_keys}
    # The source links are stored in JSON. Serialize their creation with workflow deletion.
    version_ids = [workflow.active_version_id for workflow in workflows]
    locked = WorkflowVersion.objects.select_for_update().order_by('pk').in_bulk(version_ids)
    if any(pk not in locked for pk in version_ids):
        raise WorkflowConflict()
    versions = [locked[pk] for pk in version_ids]
    definition = chain_definitions(version.as_definition() for version in versions)
    bindings = {
        f'p{index}_{offset}': reviewers
        for index, (source, reviewers) in enumerate(entries)
        for offset, node in enumerate(source.active_version.nodes.order_by('key'))
        if node.type == 'approval' and node.config['approvers']['type'] == 'acl_reviewers'
    }
    digest = sha256(','.join(str(version.pk) for version in versions).encode()).hexdigest()[:24]
    with tmp_to_org(org_id):
        workflow, _ = Workflow.objects.get_or_create(
            org_id=org_id, type=ticket_type, name=f'ACL combined {digest}',
            defaults={'is_system': True, 'comment': 'Combined ACL approval workflows.',
                      'migration_notes': {'source_versions': [str(version.pk) for version in versions]}},
        )
        workflow = Workflow.objects.select_for_update().get(pk=workflow.pk)
        if not workflow.is_system:
            raise WorkflowConfigurationError(gettext('The generated workflow name is already in use.'))
        if not workflow.active_version_id:
            publish_workflow(workflow, definition)
            Workflow.objects.filter(pk=workflow.pk).update(enabled=True)
            workflow.refresh_from_db()
    return workflow, bindings
