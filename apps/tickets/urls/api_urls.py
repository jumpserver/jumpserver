# -*- coding: utf-8 -*-
#
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = 'tickets'
router = BulkRouter()

router.register('tickets', api.TicketViewSet, 'ticket')
router.register('tickets/(?P<ticket_id>[0-9a-zA-Z\-]{36})/comments', api.TicketCommentViewSet, 'ticket-comment')


urlpatterns = [
]

urlpatterns += router.urls
