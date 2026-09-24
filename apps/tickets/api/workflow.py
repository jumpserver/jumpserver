from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from orgs.models import Organization
from orgs.utils import current_org, tmp_to_root_org
from rbac.permissions import RBACPermission
from tickets.models import Workflow, WorkflowInstance, ApprovalTask
from tickets.serializers.workflow import (
    WorkflowSerializer, WorkflowPublishSerializer, WorkflowVersionSerializer,
    WorkflowInstanceSerializer, WorkflowInstanceDetailSerializer, WorkflowEventSerializer,
    ApprovalTaskSerializer, WorkflowDecisionSerializer, WorkflowReassignSerializer,
)
from tickets.workflow.approvers import available_users
from tickets.workflow.engine import WorkflowEngine
from tickets.workflow.publication import publish_workflow
from tickets.plugins import get_ticket_plugin

__all__ = ['WorkflowViewSet', 'WorkflowInstanceViewSet', 'ApprovalTaskViewSet']


class WorkflowViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet):
    page_default_limit = 50
    page_max_limit = 200
    serializer_class = WorkflowSerializer
    permission_classes = [RBACPermission]
    perm_model = Workflow
    filterset_fields = ['type', 'enabled']
    search_fields = ['name']
    rbac_perms = {'publish': 'tickets.change_workflow', 'versions': 'tickets.view_workflow'}

    def get_queryset(self):
        # The root organization may manage global and organization definitions.
        return Workflow.objects.select_related('active_version').filter(is_system=False)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='options')
    def options_list(self, request, **kwargs):
        org_id = request.query_params.get('org_id', str(current_org.id))
        ticket_type = request.query_params.get('type', 'apply_asset')
        plugin = get_ticket_plugin(ticket_type)
        if org_id == Organization.ROOT_ID:
            if not plugin.allow_global or not plugin.global_options_permission or not request.user.has_perm(plugin.global_options_permission):
                raise PermissionDenied()
        elif not Organization.objects.filter(pk=org_id).exists() or not (
            available_users(org_id).filter(pk=request.user.pk).exists() or request.user.is_superuser
        ):
            raise PermissionDenied()
        with tmp_to_root_org():
            workflows = Workflow.objects.filter(org_id__in=[org_id, Organization.ROOT_ID], type=ticket_type, is_system=False,
                                                 enabled=True, active_version__published_at__isnull=False)
            return Response([{'id': str(workflow.pk), 'name': workflow.name, 'type': workflow.type}
                             for workflow in workflows])

    @action(detail=True, methods=['post'])
    def publish(self, request, **kwargs):
        workflow = self.get_object()
        serializer = WorkflowPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = publish_workflow(workflow, actor=request.user, **serializer.validated_data)
        return Response(WorkflowVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def versions(self, request, **kwargs):
        versions = self.get_object().versions.filter(published_at__isnull=False)
        page = self.paginate_queryset(versions)
        data = WorkflowVersionSerializer(page if page is not None else versions, many=True).data
        return self.get_paginated_response(data) if page is not None else Response(data)


class WorkflowInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    page_default_limit = 50
    page_max_limit = 200
    permission_classes = [IsAuthenticated]
    serializer_class = WorkflowInstanceSerializer
    filterset_fields = ['ticket', 'state', 'version']

    def get_queryset(self):
        qs = WorkflowInstance.objects.select_related('version').all()
        if not self.request.user.has_perm('tickets.view_workflowinstance'):
            qs = qs.filter(Q(applicant=self.request.user) | Q(node_instances__tasks__assignee=self.request.user) |
                           Q(ticket__cc_users=self.request.user)).distinct()
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkflowInstanceDetailSerializer
        return self.serializer_class

    @action(detail=True, methods=['get'])
    def events(self, request, **kwargs):
        events = self.get_object().events.all()
        page = self.paginate_queryset(events)
        data = WorkflowEventSerializer(page if page is not None else events, many=True).data
        return self.get_paginated_response(data) if page is not None else Response(data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, **kwargs):
        instance = self.get_object()
        serializer = WorkflowDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = WorkflowEngine().cancel(instance, request.user, **serializer.validated_data)
        return Response(WorkflowInstanceSerializer(instance).data)


class ApprovalTaskViewSet(viewsets.ReadOnlyModelViewSet):
    page_default_limit = 50
    page_max_limit = 200
    permission_classes = [IsAuthenticated]
    serializer_class = ApprovalTaskSerializer
    filterset_fields = ['state', 'node_instance__instance']

    def get_queryset(self):
        qs = ApprovalTask.objects.filter(assignee=self.request.user).select_related('node_instance__node')
        if not current_org.is_root():
            qs = qs.filter(node_instance__instance__org_id=current_org.id)
        return qs

    def _decide(self, request, operation):
        task = self.get_object()
        serializer_class = WorkflowReassignSerializer if operation in ('transfer', 'add_approver') else WorkflowDecisionSerializer
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if 'target' in data:
            target = available_users(task.node_instance.instance.org_id).filter(pk=data['target']).first()
            if target is None:
                raise ValidationError({'target': 'Select an active member of this organization.'})
            data['target'] = target
        instance = getattr(WorkflowEngine(), operation)(task, request.user, **data)
        return Response(WorkflowInstanceSerializer(instance).data)

    @action(detail=True, methods=['get'])
    def candidates(self, request, **kwargs):
        task = self.get_object()
        users = available_users(task.node_instance.instance.org_id).exclude(
            pk__in=task.node_instance.tasks.filter(assignee__isnull=False).values('assignee_id')
        )
        if task.node_instance.node.config['exclude_applicant']:
            users = users.exclude(pk=task.node_instance.instance.applicant_id)
        search = request.query_params.get('search', '')[:128]
        if search:
            users = users.filter(Q(name__icontains=search) | Q(username__icontains=search))
        page = self.paginate_queryset(users.order_by('name', 'id').values('id', 'name', 'username'))
        return self.get_paginated_response(page)

    @action(detail=True, methods=['post'])
    def approve(self, request, **kwargs):
        return self._decide(request, 'approve')

    @action(detail=True, methods=['post'])
    def reject(self, request, **kwargs):
        return self._decide(request, 'reject')

    @action(detail=True, methods=['post'])
    def transfer(self, request, **kwargs):
        return self._decide(request, 'transfer')

    @action(detail=True, methods=['post'], url_path='add-approver')
    def add_approver(self, request, **kwargs):
        return self._decide(request, 'add_approver')
