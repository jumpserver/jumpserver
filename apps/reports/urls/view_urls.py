# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from django.urls import path

from .. import views

__all__ = ["urlpatterns"]

app_name = "reports"

urlpatterns = [
    # Resource Task url
    path('export-pdf/', views.ExportPdfView.as_view(), name='export-pdf'),
    path('send-mail/', views.SendMailView.as_view(), name='send-mail'),
]