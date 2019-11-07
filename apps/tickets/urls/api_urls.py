# -*- coding: utf-8 -*-
#
from django.urls import path
from rest_framework.routers import DefaultRouter

from .. import api

app_name = 'tickets'
router = DefaultRouter()

router.register('tickets', api.TicketViewSet, 'ticket')
router.register('login-confirm-tickets', api.LoginConfirmTicketViewSet, 'login-confirm-ticket')
router.register('tickets/<uuid:ticket_id>/comments/', api.CommentViewSet, 'ticket-comment')


urlpatterns = [
    path('login-confirm-tickets/<uuid:pk>/actions/',
         api.LoginConfirmTicketsCreateActionApi.as_view(),
         name='login-confirm-ticket-create-action'
    ),
]

urlpatterns += router.urls
