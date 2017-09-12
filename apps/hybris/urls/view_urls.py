# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.conf.urls import url
from .. import views

app_name = 'hybris'

urlpatterns = [
    url(r'^templates/$', views.TemplateListView.as_view(), name='template-list'),
    url(r'^templates/opt/(?P<type>[A-Za-z]+)/(?P<pk>[0-9]+)/(?P<opt>.+)/$', view=views.TemplateRedirectView.as_view(),
        name='template-opt'),
    url(r'^templates/install/(?P<pk>[0-9]+)/$', views.InstallTemplateDetailView.as_view(),
        name='template-install-detail'),
    url(r'^templates/install/(?P<pk>[0-9]+)/update/$', views.InstallTemplateUpdateView.as_view(),
        name='template-install-update'),
    # url(r'^task/(?P<pk>[0-9a-zA-Z-]+)/$', views.TaskDetailView.as_view(), name='task-detail'),
    # url(r'^task/(?P<pk>[0-9a-zA-Z-]+)/run/$', views.TaskRunView.as_view(), name='task-run'),
]
