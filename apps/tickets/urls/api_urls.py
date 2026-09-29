# -*- coding: utf-8 -*-
#
from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = 'tickets'
router = BulkRouter()

router.register('tickets', api.TicketViewSet, 'ticket')
router.register('ticket-types', api.TicketTypeViewSet, 'ticket-type')
router.register('workflows', api.WorkflowViewSet, 'workflow')
router.register('workflow-instances', api.WorkflowInstanceViewSet, 'workflow-instance')
router.register('approval-tasks', api.ApprovalTaskViewSet, 'approval-task')
router.register('comments', api.CommentViewSet, 'comment')
router.register('ticket-session-relation', api.TicketSessionRelationViewSet, 'ticket-session-relation')
router.register('apply-assets', api.ApplyAssetsViewSet, 'apply-assets')
router.register('apply-nodes', api.ApplyNodesViewSet, 'apply-nodes')

urlpatterns = [
    path('tickets/<uuid:ticket_id>/session/', api.TicketSessionApi.as_view(), name='ticket-session'),
    path('super-tickets/<uuid:pk>/status/', api.SuperTicketStatusAPI.as_view(), name='super-ticket-status'),
]
urlpatterns += router.urls
