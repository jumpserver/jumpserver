# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals


from django.conf.urls import url
from .. import views

__all__ = ["urlpatterns"]

urlpatterns = [
    # TResource Task url
    url(r'^task-record/$',  views.TaskRecordListView.as_view(), name='task-record-list'),
    url(r'^task-record/(?P<pk>[0-9a-zA-Z-]+)/$',   views.TaskRecordDetailView.as_view(), name='task-record-detail'),
]