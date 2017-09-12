# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.conf.urls import url
from .. import views

app_name = 'hybris'

urlpatterns = [
    url(r'^tasks/$', views.TaskListView.as_view(), name='task-list'),
    url(r'^task/opt/(?P<type>[A-Za-z]+)/(?P<pk>[0-9]+)/(?P<opt>.+)/$', view=views.TaskRedirectView.as_view(),
        name='task-opt'),
    url(r'^task/install/(?P<pk>[0-9]+)/$', views.InstallDetailView.as_view(), name='install-detail'),
    url(r'^task/install/(?P<pk>[0-9]+)/update/$', views.InstallUpdateView.as_view(), name='install-update'),
    # url(r'^task/(?P<pk>[0-9a-zA-Z-]+)/$', views.TaskDetailView.as_view(), name='task-detail'),
    # url(r'^task/(?P<pk>[0-9a-zA-Z-]+)/run/$', views.TaskRunView.as_view(), name='task-run'),
]
