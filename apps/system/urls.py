# coding:utf-8
from rest_framework_bulk.routes import BulkRouter

from . import api

app_name = 'system'

router = BulkRouter()
router.register(r'stats', api.StatViewSet, 'stat')

urlpatterns = [
]

urlpatterns += router.urls
