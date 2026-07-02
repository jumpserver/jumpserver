from django.urls import path
from rest_framework.routers import DefaultRouter

from reports import api

app_name = 'reports'

router = DefaultRouter()
router.register('reports', api.ReportViewSet, 'report')

urlpatterns = [
    path('reports/users/', api.UserReportApi.as_view(), name='user-list'),
    path('reports/user-change-password/', api.UserChangeSecretApi.as_view(), name='user-change-password'),
    path('reports/asset-statistic/', api.AssetStatisticApi.as_view(), name='asset-statistic'),
    path('reports/asset-activity/', api.AssetActivityApi.as_view(), name='asset-activity'),
    path('reports/account-statistic/', api.AccountStatisticApi.as_view(), name='account-statistic'),
    path('reports/account-automation/', api.AccountAutomationApi.as_view(), name='account-automation'),
]

urlpatterns += router.urls