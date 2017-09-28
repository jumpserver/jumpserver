# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.conf.urls import url
from .. import views

app_name = 'devops'

urlpatterns = [
    url(r'^tasks/$', views.TaskListView.as_view(), name='task-list'),
]
