# coding: utf-8
#

from django.urls import path
from rest_framework_bulk.routes import BulkRouter
from .. import api


router = BulkRouter()
router.register('database-app-permissions', api.DatabaseAppPermissionViewSet, 'database-app-permission')
router.register('database-app-permissions-users-relations', api.DatabaseAppPermissionUserRelationViewSet, 'database-app-permissions-users-relation')
router.register('database-app-permissions-user-groups-relations', api.DatabaseAppPermissionUserGroupRelationViewSet, 'database-app-permissions-user-groups-relation')
router.register('database-app-permissions-database-apps-relations', api.DatabaseAppPermissionDatabaseAppRelationViewSet, 'database-app-permissions-database-apps-relation')

database_app_permission_urlpatterns = [

    # 授权规则中授权的用户和数据库应用
    path('database-app-permissions/<uuid:pk>/users/all/', api.DatabaseAppPermissionAllUserListApi.as_view(), name='database-app-permission-all-users'),
    path('database-app-permissions/<uuid:pk>/database-apps/all/', api.DatabaseAppPermissionAllDatabaseAppListApi.as_view(), name='database-app-permission-all-database-apps'),
]

database_app_permission_urlpatterns += router.urls


