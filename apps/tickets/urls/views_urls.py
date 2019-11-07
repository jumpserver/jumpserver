# -*- coding: utf-8 -*-
#
from django.urls import path
from .. import views

app_name = 'tickets'

urlpatterns = [
    path('login-confirm-tickets/', views.LoginConfirmTicketListView.as_view(), name='login-confirm-ticket-list'),
    path('login-confirm-tickets/<uuid:pk>/', views.LoginConfirmTicketDetailView.as_view(), name='login-confirm-ticket-detail')
]
