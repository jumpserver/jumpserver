# -*- coding: utf-8 -*-
#
from django.urls import path
from .. import views

app_name = 'orders'

urlpatterns = [
    path('login-confirm-orders/', views.LoginConfirmOrderListView.as_view(), name='login-confirm-order-list'),
    path('login-confirm-orders/<uuid:pk>/', views.LoginConfirmOrderDetailView.as_view(), name='login-confirm-order-detail')
]
