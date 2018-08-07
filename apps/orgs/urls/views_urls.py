# -*- coding: utf-8 -*-
#

from django.urls import path

from .. import views

app_name = 'orgs'


urlpatterns = [
    path('<str:pk>/switch/', views.SwitchOrgView.as_view(), name='org-switch'),
    path('switch-a-org/', views.SwitchToAOrgView.as_view(), name='switch-a-org')
]
