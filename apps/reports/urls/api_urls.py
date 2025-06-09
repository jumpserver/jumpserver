from django.urls import path

from reports import api

app_name = 'reports'

urlpatterns = [
    path('reports/', api.ReportViewSet.as_view(), name='report-list'),
]
