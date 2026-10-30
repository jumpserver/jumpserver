"""Resource amendments share the workflow lock and never cast an approval vote."""
from django.utils.translation import gettext
import copy
import json

from django.db import models
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.renderers import JSONRenderer

from orgs.utils import tmp_to_org
from tickets.plugins import get_ticket_plugin
from .errors import WorkflowConflict, WorkflowConfigurationError


def application_assets(request, org_id):
    from assets.models import Asset
    from tickets.const import TicketApplyAssetScope
    from perms.utils import AssetPermissionPermAssetUtil
    from perms.utils.permission import AssetPermissionUtil
    assets = Asset.objects.filter(org_id=org_id)
    if TicketApplyAssetScope.is_permed() or TicketApplyAssetScope.is_permed_valid():
        permissions = AssetPermissionUtil().get_permissions_for_user(
            request.user, flat=True, with_expired=TicketApplyAssetScope.is_permed())
        assets = AssetPermissionPermAssetUtil(permissions).get_all_assets().filter(org_id=org_id)
    return assets


def resource_availability(plugin, request, org_id, data=None):
    if not plugin.resource_serializer:
        raise ValidationError(gettext('This ticket type does not support resource adjustment.'))
    data = data or request.query_params
    assets = application_assets(request, org_id)
    ids = data.get('apply_assets', []) if plugin.type == 'apply_asset' else [data.get('asset')]
    if isinstance(ids, str):
        ids = ids.split(',') if ids else []
    ids = [value for value in ids if value]
    ids = serializers.ListField(child=serializers.UUIDField(), max_length=100).run_validation(ids)
    if ids and assets.filter(pk__in=ids).count() != len(set(ids)):
        raise ValidationError({'asset': gettext('Select assets available for application in this organization.')})
    selected = assets.filter(pk__in=ids)
    # Asset permission forms also accept nodes and dynamic account selectors.
    nodes = data.get('apply_nodes', []) if plugin.type == 'apply_asset' else []
    if isinstance(nodes, str):
        nodes = nodes.split(',') if nodes else []
    if nodes:
        from assets.models import Node
        node_ids = serializers.ListField(child=serializers.UUIDField(), max_length=100).run_validation(nodes)
        from tickets.api.perms import ApplyNodesViewSet
        view = ApplyNodesViewSet()
        view.request = request
        allowed = view.get_queryset().filter(pk__in=node_ids, org_id=org_id)
        if allowed.count() != len(set(node_ids)):
            raise ValidationError({'apply_nodes': gettext('Select nodes available for application in this organization.')})
        asset_ids = set(ids)
        for node in allowed:
            asset_ids.update(node.get_all_assets().filter(org_id=org_id).values_list('pk', flat=True))
        selected = assets.filter(pk__in=asset_ids)
    from accounts.models import Account
    accounts = Account.objects.filter(asset__in=selected).exclude(username='')
    if plugin.type == 'view_secret':
        from accounts.const import SecretType
        accounts = accounts.filter(is_active=True, secret_type=SecretType.PASSWORD)
    empty = not assets.exists() or (bool(ids or nodes) and not accounts.exists())
    return {'description_allowed': empty, 'has_assets': assets.exists()}


def validate_description(plugin, attrs, context):
    all_accounts = plugin.type == 'apply_asset' and attrs.get('apply_accounts') == ['@ALL']
    if not plugin.resources_pending(attrs) and not (all_accounts and attrs.get('resource_description')):
        return
    description = serializers.CharField(max_length=4096).run_validation(attrs.get('resource_description', ''))
    # Never trust a client flag or an unsuccessful resource request as proof of an empty list.
    with tmp_to_org(context['org_id']):
        empty = resource_availability(plugin, context['request'], context['org_id'], attrs)['description_allowed']
    # The original form can select "all" even when there are no concrete accounts to freeze.
    if all_accounts and empty:
        attrs['apply_accounts'] = []
    if not plugin.resources_pending(attrs):
        return
    if not empty:
        raise ValidationError({'resource_description': gettext('Select the available resources before submitting.')})
    attrs['resource_description'] = description


def check_adjustment(instance, task, user):
    from .engine import WorkflowEngine
    from .approvers import available_users, excluded_approver_ids
    WorkflowEngine._check_org(instance.org_id)
    plugin = get_ticket_plugin(instance.ticket.type)
    if (not plugin.resource_serializer or 'legacy' in instance.context or instance.state != 'running'
            or task.state != 'pending' or task.node_instance.state != 'running'
            or (task.node_instance.deadline and task.node_instance.deadline <= timezone.now())):
        raise WorkflowConflict(gettext('This request cannot be adjusted now.'))
    if (task.assignee_id != user.pk or not available_users(instance.org_id).filter(pk=user.pk).exists()
            or str(user.pk) in excluded_approver_ids(task.node_instance.node.config, instance.context, instance.applicant_id)):
        raise PermissionDenied()
    with tmp_to_org(instance.org_id):
        if not {'assets.view_asset', 'accounts.view_account'}.issubset(user.get_all_permissions()):
            raise PermissionDenied(gettext('Adjusting resources requires asset and account query permissions in this organization.'))
    return plugin


def adjustment_status(instance, user):
    plugin = get_ticket_plugin(instance.ticket.type)
    if not plugin.resource_serializer or 'legacy' in instance.context:
        return None
    status = {'revision': instance.context.get('resource_revision', 0),
              'pending': instance.context.get('resources_pending', False), 'can_adjust': False}
    if not user:
        return status
    task = instance.node_instances.filter(state='running').values_list('tasks', flat=True)
    from tickets.models import ApprovalTask
    task = ApprovalTask.objects.filter(pk__in=task, assignee=user, state='pending').select_related('node_instance__node').first()
    if task:
        try:
            check_adjustment(instance, task, user)
        except (PermissionDenied, WorkflowConflict):
            pass
        else:
            status['can_adjust'] = True
            from tickets.plugins.schema import request_fields
            serializer = plugin.get_resource_serializer()
            status['fields'] = request_fields(serializer)
            status['values'] = {name: value for name, value in instance.ticket.request_data.items()
                                if name in serializer.fields}
            if 'apply_actions' in status['values']:
                status['values']['apply_actions'] = serializer.fields['apply_actions'].to_representation(
                    status['values']['apply_actions'])
    return status


def check_revision(instance, revision):
    current = instance.context.get('resource_revision', 0)
    if (current or revision is not None) and revision != current:
        raise WorkflowConflict(gettext('The request was adjusted. Refresh and review the current resources.'))


def adjust_resources(engine, instance, task, user, data, reason, revision):
    from .business import build_context
    from .definition import json_snapshot
    plugin = check_adjustment(instance, task, user)
    check_revision(instance, revision)
    ticket = copy.copy(instance.ticket)
    with tmp_to_org(instance.org_id):
        serializer = plugin.get_resource_serializer(data=data, context={
            'org_id': instance.org_id, 'request': type('ResourceRequest', (), {'user': user})(), 'ticket': ticket})
        serializer.is_valid(raise_exception=True)
        before = ticket.request_data
        ticket.request_data = {**before, **json.loads(JSONRenderer().render(serializer.validated_data))}
        context = build_context(ticket)
        context['applicant'] = instance.context['applicant']
        context['resource_revision'] = instance.context.get('resource_revision', 0) + 1
        plugin.validate_submission(ticket, context)
        # An owner task only covers the assets and owners for which it was assigned.
        owners_changed = task.node_instance.node.config['approvers']['type'] == 'asset_owner' and (
            {asset['id']: asset['owner_ids'] for asset in instance.context['assets']} !=
            {asset['id']: asset['owner_ids'] for asset in context['assets']}
        )
        # The only mutation path for an instance snapshot: under its row lock, with a revision and audit event.
        qs = type(instance).objects.filter(pk=instance.pk, context=instance.context)
        if models.QuerySet.update(qs, context=json_snapshot(context)) != 1:
            raise WorkflowConflict()
        instance.context = context
        type(ticket).objects.filter(pk=ticket.pk).update(request_data=ticket.request_data, date_updated=timezone.now())
        instance.ticket = ticket
    restarted = owners_changed or instance.node_instances.filter(tasks__state='approved').exists()
    # Conditions already traversed may depend on the amended scope even before a vote.
    restarted = restarted or instance.node_instances.filter(node__type='condition').exists()
    engine._event(instance, 'resources.adjusted', node=task.node_instance, task=task, actor=user,
                  before=before, after=ticket.request_data, reason=reason,
                  revision=context['resource_revision'], restarted=restarted)
    if restarted:
        engine._close_pending(instance)
        instance.node_instances.filter(state='running').update(state='cancelled', date_finished=timezone.now())
        # Fail atomically: a bad new branch must not discard the pending review or the previous scope.
        engine._execute(instance, instance.version.nodes.get(type='start'))
        if instance.state != 'running':
            raise WorkflowConfigurationError(gettext('An adjusted request must pass an approval node before completion.'))
    return instance


def resource_options(instance, task, user, params):
    from assets.models import Asset, Node
    from accounts.models import Account
    plugin = check_adjustment(instance, task, user)
    with tmp_to_org(instance.org_id):
        resource = params.get('resource', 'asset')
        search = params.get('search', '')[:128]
        assets = Asset.objects.filter(org_id=instance.org_id, is_active=True)
        if resource == 'asset':
            return list(assets.filter(Q(name__icontains=search) | Q(address__icontains=search))
                        .order_by('name', 'id').values('id', 'name', 'address')[:100])
        if resource == 'node' and plugin.type == 'apply_asset':
            if 'assets.view_node' not in user.get_all_permissions():
                raise PermissionDenied()
            return list(Node.objects.filter(org_id=instance.org_id, full_value__icontains=search)
                        .order_by('full_value').values('id', 'full_value')[:100])
        if resource != 'account':
            raise ValidationError({'resource': gettext('Unknown resource field.')})
        ids = serializers.ListField(child=serializers.UUIDField(), max_length=100).run_validation(
            params.get('assets', '').split(',') if params.get('assets') else [])
        if assets.filter(pk__in=ids).count() != len(set(ids)):
            raise ValidationError({'assets': gettext('Select active assets in the ticket organization.')})
        accounts = Account.objects.filter(asset__in=assets.filter(pk__in=ids)).exclude(username='')
        if plugin.type == 'view_secret':
            from accounts.const import SecretType
            accounts = accounts.filter(secret_type=SecretType.PASSWORD, is_active=True)
        return list(accounts.order_by('username').values_list('username', flat=True).distinct()[:1000])
