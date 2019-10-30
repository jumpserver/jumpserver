# -*- coding: utf-8 -*-
#
from django.urls import path
from rest_framework.routers import DefaultRouter

from .. import api

app_name = 'orders'
router = DefaultRouter()

router.register('login-confirm-orders', api.LoginConfirmOrderViewSet, 'login-confirm-order')

urlpatterns = [
    path('login-confirm-order/<uuid:pk>/actions/',
         api.LoginConfirmOrderCreateActionApi.as_view(),
         name='login-confirm-order-create-action'
         ),
]

urlpatterns += router.urls
