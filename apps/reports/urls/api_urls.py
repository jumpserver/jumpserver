from django.urls import path

from reports import api

app_name = 'reports'

urlpatterns = [
    path('reports/', api.ReportViewSet.as_view(), name='report-list'),
    path('reports/users/', api.UserReportApi.as_view(), name='user-list'),
    path('reports/user-change-password/', api.UserChangeSecretApi.as_view(), name='user-change-password')
]
