# -*- coding: utf-8 -*-
#
from django.urls import path
from rest_framework.routers import DefaultRouter

from .. import api

app_name = 'tickets'
router = DefaultRouter()

router.register('tickets', api.TicketViewSet, 'ticket')
router.register('tickets/(?P<ticket_id>[0-9a-zA-Z\-]{36})/comments', api.TicketCommentViewSet, 'ticket-comment')
router.register('login-confirm-tickets', api.LoginConfirmTicketViewSet, 'login-confirm-ticket')


urlpatterns = [
]

urlpatterns += router.urls
