# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.urls import path
from .. import views

__all__ = ["urlpatterns"]

app_name = "audits"

urlpatterns = [
    path('ftp-log/', views.FTPLogListView.as_view(), name='ftp-log-list'),
]
