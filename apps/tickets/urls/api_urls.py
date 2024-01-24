# -*- coding: utf-8 -*-
#
from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = 'tickets'
router = BulkRouter()

router.register('tickets', api.TicketViewSet, 'ticket')
router.register('flows', api.TicketFlowViewSet, 'flows')
router.register('comments', api.CommentViewSet, 'comment')
router.register('apply-asset-tickets', api.ApplyAssetTicketViewSet, 'apply-asset-ticket')
router.register('apply-login-tickets', api.ApplyLoginTicketViewSet, 'apply-login-ticket')
router.register('apply-command-tickets', api.ApplyCommandTicketViewSet, 'apply-command-ticket')
router.register('apply-login-asset-tickets', api.ApplyLoginAssetTicketViewSet, 'apply-login-asset-ticket')
router.register('ticket-session-relation', api.TicketSessionRelationViewSet, 'ticket-session-relation')
router.register('apply-assets', api.ApplyAssetsViewSet, 'ticket-session-relation')
router.register('apply-nodes', api.ApplyNodesViewSet, 'ticket-session-relation')

urlpatterns = [
    path('tickets/<uuid:ticket_id>/session/', api.TicketSessionApi.as_view(), name='ticket-session'),
    path('super-tickets/<uuid:pk>/status/', api.SuperTicketStatusAPI.as_view(), name='super-ticket-status'),
]
urlpatterns += router.urls
