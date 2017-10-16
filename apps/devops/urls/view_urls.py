# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.conf.urls import url
from .. import views

app_name = 'devops'

urlpatterns = [
    url(r'^task/$', views.TaskListView.as_view(), name='task-list'),
    url(r'^task/create$', views.TaskCreateView.as_view(), name='task-create'),
]
