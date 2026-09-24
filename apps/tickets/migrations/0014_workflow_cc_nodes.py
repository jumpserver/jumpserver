from django.db import migrations, models
from django.utils import timezone


def move_workflow_cc_to_nodes(apps, schema_editor):
    """Publish a new version so running instances keep their original graph."""
    Workflow = apps.get_model('tickets', 'Workflow')
    Version = apps.get_model('tickets', 'WorkflowVersion')
    Node = apps.get_model('tickets', 'WorkflowNode')
    Edge = apps.get_model('tickets', 'WorkflowEdge')
    db = schema_editor.connection.alias

    for workflow in Workflow.objects.using(db).all().iterator():
        users = sorted(str(pk) for pk in workflow.cc_users.values_list('pk', flat=True))
        if not users:
            continue
        if not workflow.active_version_id:
            notes = dict(workflow.migration_notes or {})
            notes['unpublished_cc_user_ids'] = users
            Workflow.objects.using(db).filter(pk=workflow.pk).update(migration_notes=notes)
            continue
        previous = Version.objects.using(db).get(pk=workflow.active_version_id)
        version = Version.objects.using(db).create(
            workflow_id=workflow.pk,
            number=(Version.objects.using(db).filter(workflow_id=workflow.pk).order_by('-number').values_list('number', flat=True).first() or 0) + 1,
            published_at=timezone.now(),
            created_by='Workflow CC migration',
        )
        old_nodes = list(Node.objects.using(db).filter(version_id=previous.pk))
        nodes = {}
        for old in old_nodes:
            nodes[old.pk] = Node.objects.using(db).create(
                version_id=version.pk, key=old.key, type=old.type, name=old.name,
                config=old.config, position_x=old.position_x, position_y=old.position_y,
            )
        start = next(node for node in old_nodes if node.type == 'start')
        key = 'cc_legacy'
        keys = {node.key for node in old_nodes}
        index = 1
        while key in keys:
            key = f'cc_legacy_{index}'
            index += 1
        cc = Node.objects.using(db).create(
            version_id=version.pk, key=key, type='cc', name='CC', config={'users': users},
            position_x=start.position_x, position_y=start.position_y + 60,
        )
        for old in Edge.objects.using(db).filter(version_id=previous.pk):
            Edge.objects.using(db).create(
                version_id=version.pk,
                source_id=cc.pk if old.source_id == start.pk else nodes[old.source_id].pk,
                target_id=nodes[old.target_id].pk,
                condition=old.condition, priority=old.priority,
            )
        Edge.objects.using(db).create(
            version_id=version.pk, source_id=nodes[start.pk].pk, target_id=cc.pk,
            condition=None, priority=0,
        )
        Workflow.objects.using(db).filter(pk=workflow.pk).update(active_version_id=version.pk)


class Migration(migrations.Migration):
    dependencies = [('tickets', '0013_ticket_plugins')]

    operations = [
        migrations.RunPython(move_workflow_cc_to_nodes, migrations.RunPython.noop),
        migrations.RemoveField(model_name='workflow', name='cc_users'),
        migrations.AlterField(
            model_name='workflownode', name='type',
            field=models.CharField(choices=[
                ('start', 'Start'), ('approval', 'Approval'), ('condition', 'Condition'),
                ('cc', 'CC'), ('end', 'End'),
            ], max_length=16),
        ),
    ]
