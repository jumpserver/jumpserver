# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals


from django.conf.urls import url
from .. import views

__all__ = ["urlpatterns"]

app_name = "audits"

urlpatterns = [
    url(r'^ftp-log/$', views.FTPLogListView.as_view(), name='ftp-log-list'),
]
