# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals


from django.conf.urls import url
from .. import views

app_name = 'hybris'

urlpatterns = [
    url(r'^conf/$', views.HybrisConfView.as_view(), name='conf'),
    # url(r'^task/(?P<pk>[0-9a-zA-Z-]+)/$', views.TaskDetailView.as_view(), name='task-detail'),
    # url(r'^task/(?P<pk>[0-9a-zA-Z-]+)/run/$', views.TaskRunView.as_view(), name='task-run'),
]