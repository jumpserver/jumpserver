# coding:utf-8
#

from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = 'applications'

router = BulkRouter()
router.register(r'remote-app', api.RemoteAppViewSet, 'remote-app')

urlpatterns = [
    path('remote-apps/<uuid:pk>/connection-info/',
         api.RemoteAppConnectionInfoApi.as_view(),
         name='remote-app-connection-info')
]

urlpatterns += router.urls
