import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models
import tickets.plugins.registry
from uuid import UUID


def mark_legacy_system_tickets(apps, schema_editor):
    # Django creates deferred indexes after the data updates in this atomic migration.
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('SET CONSTRAINTS ALL IMMEDIATE')
    # These types were only created by ACL entrypoints before origin was stored.
    Ticket = apps.get_model('tickets', 'Ticket')
    Ticket.objects.using(schema_editor.connection.alias).filter(
        type__in=['login_confirm', 'login_asset_confirm', 'command_confirm'],
    ).update(origin='system')


def migrate_payloads(apps, schema_editor):
    db = schema_editor.connection.alias
    Ticket = apps.get_model('tickets', 'Ticket')

    def copy(model_name, values):
        Model = apps.get_model('tickets', model_name)
        rows = Model.objects.using(db).all()
        if model_name == 'ApplyAssetTicket':
            rows = rows.prefetch_related('apply_assets', 'apply_nodes')
        pending = []
        for row in rows.iterator(chunk_size=500):
            payload = dict(row.request_data or {})
            payload.update(values(row))
            pending.append(Ticket(pk=row.pk, request_data=payload))
            if len(pending) == 500:
                Ticket.objects.using(db).bulk_update(pending, ['request_data'])
                pending.clear()
        if pending:
            Ticket.objects.using(db).bulk_update(pending, ['request_data'])

    copy('ApplyAssetTicket', lambda row: {
        'apply_permission_name': row.apply_permission_name,
        'apply_assets': [str(asset.pk) for asset in row.apply_assets.all()],
        'apply_nodes': [str(node.pk) for node in row.apply_nodes.all()],
        'apply_accounts': row.apply_accounts,
        'apply_actions': row.apply_actions,
        'apply_date_start': row.apply_date_start.isoformat() if row.apply_date_start else None,
        'apply_date_expired': row.apply_date_expired.isoformat() if row.apply_date_expired else None,
        'apply_expire_soon_notice_minutes': row.apply_expire_soon_notice_minutes,
    })
    copy('ApplyLoginTicket', lambda row: {
        'apply_login_ip': row.apply_login_ip,
        'apply_login_city': row.apply_login_city,
        'apply_login_datetime': row.apply_login_datetime.isoformat() if row.apply_login_datetime else None,
    })
    copy('ApplyLoginAssetTicket', lambda row: {
        'apply_login_user': str(row.apply_login_user_id) if row.apply_login_user_id else None,
        'apply_login_asset': str(row.apply_login_asset_id) if row.apply_login_asset_id else None,
        'apply_login_account': row.apply_login_account,
    })
    copy('ApplyCommandTicket', lambda row: {
        'apply_run_user': str(row.apply_run_user_id) if row.apply_run_user_id else None,
        'apply_run_asset': row.apply_run_asset,
        'apply_run_command': row.apply_run_command,
        'apply_run_account': row.apply_run_account,
        'apply_from_session': str(row.apply_from_session_id) if row.apply_from_session_id else None,
        'apply_from_cmd_filter_acl': str(row.apply_from_cmd_filter_acl_id) if row.apply_from_cmd_filter_acl_id else None,
    })


def backfill_beneficiaries(apps, schema_editor):
    db = schema_editor.connection.alias
    Ticket = apps.get_model('tickets', 'Ticket')
    Beneficiary = apps.get_model('tickets', 'TicketBeneficiary')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))

    def insert(rows):
        ids = {str(user_id) for _, user_id in rows}
        valid = {str(pk) for pk in User.objects.using(db).filter(pk__in=ids).values_list('pk', flat=True)}
        Beneficiary.objects.using(db).bulk_create([
            Beneficiary(ticket_id=ticket_id, user_id=user_id)
            for ticket_id, user_id in rows if str(user_id) in valid
        ], ignore_conflicts=True)

    batch = []
    tickets = Ticket.objects.using(db).filter(type='apply_asset').values('id', 'applicant_id', 'request_data')
    for ticket in tickets.iterator(chunk_size=500):
        users = (ticket['request_data'] or {}).get('apply_users') or [ticket['applicant_id']]
        if not isinstance(users, list):
            continue
        for user_id in users:
            try:
                batch.append((ticket['id'], str(UUID(str(user_id)))))
            except (TypeError, ValueError, AttributeError):
                continue
        if len(batch) >= 500:
            insert(batch)
            batch.clear()
    if batch:
        insert(batch)


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0009_ticketassignee_assignee_display_and_more'),
        ('authentication', '0012_connection_token_ticket'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('name', models.CharField(max_length=128, verbose_name='Name')),
                ('type', models.CharField(choices=[('general', 'General'), ('apply_asset', 'Apply for asset'), ('login_confirm', 'Login confirm'), ('command_confirm', 'Command confirm'), ('login_asset_confirm', 'Login asset confirm')], max_length=64, verbose_name='Type')),
                ('enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('legacy_flow_id', models.UUIDField(editable=False, null=True, unique=True)),
                ('migration_notes', models.JSONField(default=dict, editable=False)),
            ],
            options={
                'verbose_name': 'Approval workflow',
                'default_permissions': ('add', 'change', 'view'),
                'ordering': ['name', 'id'],
            },
        ),
        migrations.CreateModel(
            name='WorkflowNode',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('key', models.CharField(max_length=64)),
                ('type', models.CharField(choices=[('start', 'Start'), ('approval', 'Approval'), ('condition', 'Condition'), ('end', 'End')], max_length=16)),
                ('name', models.CharField(blank=True, max_length=128)),
                ('config', models.JSONField(default=dict)),
                ('position_x', models.IntegerField(default=0)),
                ('position_y', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Workflow node',
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='ApprovalTask',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('assignee_snapshot', models.JSONField(default=dict, editable=False)),
                ('state', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('transferred', 'Transferred'), ('cancelled', 'Cancelled'), ('expired', 'Expired')], default='pending', max_length=16)),
                ('is_added', models.BooleanField(default=False)),
                ('date_finished', models.DateTimeField(null=True)),
                ('assignee', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approval_tasks', to=settings.AUTH_USER_MODEL)),
                ('predecessor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='successors', to='tickets.approvaltask')),
            ],
            options={
                'verbose_name': 'Approval task',
                'ordering': ['date_created', 'id'],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='WorkflowInstance',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('context', models.JSONField(default=dict, editable=False)),
                ('state', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled'), ('expired', 'Expired'), ('error', 'Error')], default='pending', max_length=16)),
                ('date_started', models.DateTimeField(null=True)),
                ('date_finished', models.DateTimeField(null=True)),
                ('applicant', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('ticket', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='workflow_instance', to='tickets.ticket')),
            ],
            options={
                'verbose_name': 'Workflow instance',
                'ordering': ['-date_created', 'id'],
                'default_permissions': ('view',),
            },
        ),
        migrations.CreateModel(
            name='WorkflowNodeInstance',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('state', models.CharField(choices=[('running', 'Running'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('skipped', 'Skipped'), ('cancelled', 'Cancelled')], default='running', max_length=16)),
                ('required', models.PositiveIntegerField(default=0)),
                ('deadline', models.DateTimeField(db_index=True, null=True)),
                ('date_finished', models.DateTimeField(null=True)),
                ('result', models.JSONField(default=dict)),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='node_instances', to='tickets.workflowinstance')),
                ('node', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='instances', to='tickets.workflownode')),
            ],
            options={
                'verbose_name': 'Workflow node instance',
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='WorkflowEvent',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('type', models.CharField(max_length=64)),
                ('actor_snapshot', models.JSONField(default=dict, editable=False)),
                ('data', models.JSONField(default=dict)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('task', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='tickets.approvaltask')),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='events', to='tickets.workflowinstance')),
                ('node_instance', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='tickets.workflownodeinstance')),
            ],
            options={
                'verbose_name': 'Workflow event',
                'ordering': ['id'],
                'default_permissions': (),
            },
        ),
        migrations.AddField(
            model_name='approvaltask',
            name='node_instance',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tasks', to='tickets.workflownodeinstance'),
        ),
        migrations.CreateModel(
            name='WorkflowVersion',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('number', models.PositiveIntegerField()),
                ('published_at', models.DateTimeField(editable=False, null=True)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='versions', to='tickets.workflow')),
            ],
            options={
                'verbose_name': 'Workflow version',
                'default_permissions': (),
                'ordering': ['-number'],
            },
        ),
        migrations.AddField(
            model_name='workflownode',
            name='version',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nodes', to='tickets.workflowversion'),
        ),
        migrations.AddField(
            model_name='workflowinstance',
            name='version',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='instances', to='tickets.workflowversion'),
        ),
        migrations.CreateModel(
            name='WorkflowEdge',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('condition', models.BooleanField(null=True)),
                ('priority', models.PositiveIntegerField(default=0)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outgoing', to='tickets.workflownode')),
                ('target', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incoming', to='tickets.workflownode')),
                ('version', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='edges', to='tickets.workflowversion')),
            ],
            options={
                'verbose_name': 'Workflow edge',
                'default_permissions': (),
            },
        ),
        migrations.AddField(
            model_name='workflow',
            name='active_version',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='tickets.workflowversion'),
        ),
        migrations.AddIndex(
            model_name='approvaltask',
            index=models.Index(fields=['assignee', 'state'], name='tickets_task_assignee_state'),
        ),
        migrations.AddConstraint(
            model_name='approvaltask',
            constraint=models.UniqueConstraint(fields=('node_instance', 'assignee'), name='tickets_approval_task_user_uniq'),
        ),
        migrations.AddConstraint(
            model_name='workflowversion',
            constraint=models.UniqueConstraint(fields=('workflow', 'number'), name='tickets_workflow_version_uniq'),
        ),
        migrations.AddConstraint(
            model_name='workflownode',
            constraint=models.UniqueConstraint(fields=('version', 'key'), name='tickets_workflow_node_key_uniq'),
        ),
        migrations.AddConstraint(
            model_name='workflowedge',
            constraint=models.UniqueConstraint(fields=('version', 'source', 'target'), name='tickets_workflow_edge_uniq'),
        ),
        migrations.AddConstraint(
            model_name='workflow',
            constraint=models.UniqueConstraint(fields=('org_id', 'type', 'name'), name='tickets_workflow_org_name_uniq'),
        ),
        migrations.AddField(
            model_name='ticket',
            name='workflow',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tickets', to='tickets.workflow', verbose_name='Workflow'),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='state',
            field=models.CharField(choices=[('all', 'All'), ('pending', 'Ticket open'), ('closed', 'Ticket closed'), ('approved', 'Ticket approved'), ('rejected', 'Ticket rejected'), ('expired', 'Expired'), ('error', 'Error')], default='pending', max_length=16, verbose_name='State'),
        ),
        migrations.AlterField(
            model_name='ticketassignee',
            name='state',
            field=models.CharField(choices=[('all', 'All'), ('pending', 'Ticket open'), ('closed', 'Ticket closed'), ('approved', 'Ticket approved'), ('rejected', 'Ticket rejected'), ('expired', 'Expired'), ('error', 'Error')], default='pending', max_length=64),
        ),
        migrations.AddField(
            model_name='workflow', name='is_system',
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AlterModelOptions(
            name='workflownodeinstance',
            options={'default_permissions': (), 'ordering': ['date_created', 'id'], 'verbose_name': 'Workflow node instance'},
        ),
        migrations.AddField(
            model_name='ticket',
            name='request_data',
            field=models.JSONField(blank=True, default=dict, verbose_name='Request parameters'),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='type',
            field=models.CharField(choices=tickets.plugins.registry.ticket_type_choices, default='general', max_length=64, verbose_name='Type'),
        ),
        migrations.AlterField(
            model_name='workflow',
            name='type',
            field=models.CharField(choices=tickets.plugins.registry.ticket_type_choices, max_length=64, verbose_name='Type'),
        ),
        migrations.AlterField(
            model_name='workflownode', name='type',
            field=models.CharField(choices=[
                ('start', 'Start'), ('approval', 'Approval'), ('condition', 'Condition'),
                ('cc', 'CC'), ('end', 'End'),
            ], max_length=16),
        ),
        migrations.AddField(
            model_name='ticket', name='origin',
            field=models.CharField(
                choices=[('manual', 'Manual request'), ('system', 'System triggered')],
                default='manual', max_length=16, verbose_name='Ticket origin',
            ),
        ),
        migrations.RunPython(mark_legacy_system_tickets, migrations.RunPython.noop),
        migrations.RunPython(migrate_payloads),
        migrations.DeleteModel(name='ApplyAssetTicket'),
        migrations.DeleteModel(name='ApplyLoginTicket'),
        migrations.DeleteModel(name='ApplyLoginAssetTicket'),
        migrations.DeleteModel(name='ApplyCommandTicket'),
        migrations.AlterModelOptions(
            name='workflow',
            options={
                'ordering': ['name', 'id'],
                'verbose_name': 'Approval workflow',
                'default_permissions': ('add', 'change', 'view'),
                'permissions': [('apply_asset_for_others', 'Apply for asset access on behalf of another user')],
            },
        ),
        migrations.CreateModel(
            name='TicketBeneficiary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             related_name='beneficiaries', to='tickets.ticket')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='benefiting_tickets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'default_permissions': (), 'verbose_name': 'Ticket beneficiary',
                'unique_together': {('ticket', 'user')},
            },
        ),
        migrations.RunPython(backfill_beneficiaries, migrations.RunPython.noop),
        migrations.CreateModel(
            name='TicketSecretAccess',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('account_id', models.UUIDField()),
                ('user_id', models.UUIDField()),
                ('org_id', models.CharField(max_length=36)),
                ('expires_at', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             related_name='secret_accesses', to='tickets.ticket')),
            ],
            options={'default_permissions': ()},
        ),
        migrations.AddConstraint(
            model_name='ticketsecretaccess',
            constraint=models.UniqueConstraint(fields=('ticket', 'account_id'), name='tickets_secret_ticket_account_uniq'),
        ),
        migrations.AddIndex(
            model_name='ticketsecretaccess',
            index=models.Index(fields=['user_id', 'expires_at'], name='tickets_secret_user_expire'),
        ),
        migrations.CreateModel(
            name='TicketTransferExecution',
            fields=[
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('ticket', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, related_name='transfer_execution', serialize=False, to='tickets.ticket')),
                ('state', models.CharField(db_index=True, default='queued', max_length=16)),
                ('files', models.JSONField(default=list)),
                ('remote_addr', models.GenericIPAddressField(null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_started', models.DateTimeField(null=True)),
                ('date_finished', models.DateTimeField(null=True)),
                ('dispatch_after', models.DateTimeField(null=True)),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='TicketTransferFile',
            fields=[
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('size', models.PositiveBigIntegerField(default=0)),
                ('sha256', models.CharField(max_length=64)),
                ('kind', models.CharField(default='upload', max_length=8)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('purged_at', models.DateTimeField(null=True)),
                ('owner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('ticket', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='transfer_files', to='tickets.ticket')),
            ],
            options={
                'default_permissions': (),
            },
        ),
    ]
