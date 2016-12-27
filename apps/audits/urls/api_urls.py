from django.conf.urls import url
from rest_framework import routers

from .. import api

app_name = 'audits'


router = routers.DefaultRouter()
router.register(r'v1/proxy-log/', api.ProxyLogViewSet, 'proxy-log')
router.register(r'v1/command-log/', api.CommandLogViewSet, 'command-log')

urlpatterns = router.urls

