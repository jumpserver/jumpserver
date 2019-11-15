# -*- coding: utf-8 -*-
#
from django.urls import path
from .. import views

app_name = 'tickets'

urlpatterns = [
    path('tickets/', views.TicketListView.as_view(), name='ticket-list'),
    path('tickets/<uuid:pk>/', views.TicketDetailView.as_view(), name='ticket-detail'),
]
