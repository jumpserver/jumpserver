# coding:utf-8
#
from django.urls import path
from rest_framework_bulk.routes import BulkRouter
from .. import api


app_name = 'applications'


router = BulkRouter()
router.register(r'applications', api.ApplicationViewSet, 'application')


urlpatterns = [
    path('remote-apps/<uuid:pk>/connection-info/', api.RemoteAppConnectionInfoApi.as_view(), name='remote-app-connection-info'),
    path('application-users/', api.ApplicationUserListApi.as_view(), name='application-user'),
    path('application-user-auth-infos/', api.ApplicationUserAuthInfoListApi.as_view(), name='application-user-auth-info')
]


urlpatterns += router.urls
