# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals


from django.conf.urls import url
from ops import views as page_view

__all__ = ["urlpatterns"]

urlpatterns = [
    # TResource Task url
    url(r'^task/list$',   page_view.TaskListView.as_view(),   name='page-task-list'),
    url(r'^task/create$', page_view.TaskCreateView.as_view(), name='page-task-create'),
    url(r'^task/(?P<pk>[0-9]+)/detail$', page_view.TaskDetailView.as_view(), name='page-task-detail'),
    url(r'^task/(?P<pk>[0-9]+)/update$', page_view.TaskUpdateView.as_view(), name='page-task-update'),
]