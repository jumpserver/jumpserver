# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.conf.urls import url
from .. import views

app_name = 'devops'

urlpatterns = [
    url(r'^task/$', views.TaskListView.as_view(), name='task-list'),
    url(r'^task/create$', views.TaskCreateView.as_view(), name='task-create'),
    url(r'^task/(?P<pk>[0-9]+)/update/$', views.TaskUpdateView.as_view(), name='task-update'),
    url(r'^task/(?P<pk>[0-9]+)/detail/$', views.TaskDetailView.as_view(), name='task-detail'),
    url(r'^record/$', views.RecordListView.as_view(), name='record-list'),
    url(r'^record/(?P<pk>[0-9a-zA-Z-]+)/$', views.RecordDetailView.as_view(), name='record-detail'),
]
