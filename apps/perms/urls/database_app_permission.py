# coding: utf-8
# 
from rest_framework_bulk.routes import BulkRouter
from .. import api


router = BulkRouter()
router.register('database-app-permissions', api.DatabaseAppPermissionViewSet, 'database-app-permission')

database_app_permission_urlpatterns = [

]

database_app_permission_urlpatterns += router.urls


