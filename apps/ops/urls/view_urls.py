# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals


from django.conf.urls import url
from ops import views as page_view

__all__ = ["urlpatterns"]

urlpatterns = [
    # TResource Task url
    url(r'^task/list$',   page_view.TaskListView.as_view(), name='page-task-list'),
]