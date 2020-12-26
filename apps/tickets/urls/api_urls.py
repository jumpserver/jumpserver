# -*- coding: utf-8 -*-
#
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = 'tickets'
router = BulkRouter()

# router.register('tickets/request-asset-perm/assignees', api.OldAssigneeViewSet, 'ticket-request-asset-perm-assignee')
# router.register('tickets/request-asset-perm', api.RequestAssetPermTicketViewSet, 'ticket-request-asset-perm')

router.register('tickets', api.TicketViewSet, 'ticket')
router.register('assignees', api.AssigneeViewSet, 'assignee')
router.register('comments', api.CommentViewSet, 'comment')


urlpatterns = [
]

urlpatterns += router.urls
