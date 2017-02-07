from django.conf.urls import url
from rest_framework import routers

from .. import api

app_name = 'audits'

router = routers.DefaultRouter()
router.register(r'v1/proxy-log', api.ProxyLogViewSet, 'proxy-log')
router.register(r'v1/command-log', api.CommandLogViewSet, 'command-log')
router.register(r'v1/record-log', api.RecordLogViewSet, 'record-log')

urlpatterns = [
    url(r'^v1/proxy-log/receive/$', api.ProxyLogReceiveView.as_view(),
        name='proxy-log-receive'),
]

urlpatterns += router.urls
