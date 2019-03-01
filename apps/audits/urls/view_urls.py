# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.urls import path
from .. import views

__all__ = ["urlpatterns"]

app_name = "audits"

urlpatterns = [
    path('login-log/', views.LoginLogListView.as_view(), name='login-log-list'),
    path('ftp-log/', views.FTPLogListView.as_view(), name='ftp-log-list'),
    path('operate-log/', views.OperateLogListView.as_view(), name='operate-log-list'),
    path('password-change-log/', views.PasswordChangeLogList.as_view(), name='password-change-log-list'),
    path('command-execution-log/', views.CommandExecutionListView.as_view(), name='command-execution-log-list'),
    path('login-log/export/', views.LoginLogExportView.as_view(), name='login-log-export'),
]
