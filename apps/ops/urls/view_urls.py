# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from django.urls import path

from .. import views

__all__ = ["urlpatterns"]

app_name = "ops"

urlpatterns = [
    # Resource Task url
    path('celery/task/<uuid:pk>/log/', views.CeleryTaskLogView.as_view(), name='celery-task-log'),
]