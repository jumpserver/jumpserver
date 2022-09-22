# coding:utf-8
#
from django.urls import path
from rest_framework_bulk.routes import BulkRouter
from .. import api


app_name = 'applications'


router = BulkRouter()
router.register(r'applications', api.ApplicationViewSet, 'application')
router.register(r'accounts', api.ApplicationAccountViewSet, 'application-account')
router.register(r'system-users-apps-relations', api.SystemUserAppRelationViewSet, 'system-users-apps-relation')
router.register(r'account-secrets', api.ApplicationAccountSecretViewSet, 'application-account-secret')


urlpatterns = [
    path('remote-apps/<uuid:pk>/connection-info/', api.RemoteAppConnectionInfoApi.as_view(), name='remote-app-connection-info'),
    # path('accounts/', api.ApplicationAccountViewSet.as_view(), name='application-account'),
    # path('account-secrets/', api.ApplicationAccountSecretViewSet.as_view(), name='application-account-secret')
]


urlpatterns += router.urls
