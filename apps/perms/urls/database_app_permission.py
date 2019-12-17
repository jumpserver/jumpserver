# coding: utf-8
#

from django.urls import path
from rest_framework_bulk.routes import BulkRouter
from .. import api


router = BulkRouter()
router.register('database-app-permissions', api.DatabaseAppPermissionViewSet, 'database-app-permission')
router.register('database-app-permissions-users-relations', api.DatabaseAppPermissionUserRelationViewSet, 'database-app-permissions-users-relation')
router.register('database-app-permissions-user-groups-relations', api.DatabaseAppPermissionUserGroupRelationViewSet, 'database-app-permissions-user-groups-relation')

database_app_permission_urlpatterns = [
    path('database-app-permissions/<uuid:pk>/users/all/', api.DatabaseAppPermissionAllUserListApi.as_view(), name='database-app-permission-all-users'),
]

database_app_permission_urlpatterns += router.urls


