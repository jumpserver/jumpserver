# coding: utf-8
#

from django.urls import path, include
from rest_framework_bulk.routes import BulkRouter
from .. import api


router = BulkRouter()
router.register('database-app-permissions', api.DatabaseAppPermissionViewSet, 'database-app-permission')
router.register('database-app-permissions-users-relations', api.DatabaseAppPermissionUserRelationViewSet, 'database-app-permissions-users-relation')
router.register('database-app-permissions-user-groups-relations', api.DatabaseAppPermissionUserGroupRelationViewSet, 'database-app-permissions-user-groups-relation')
router.register('database-app-permissions-database-apps-relations', api.DatabaseAppPermissionDatabaseAppRelationViewSet, 'database-app-permissions-database-apps-relation')
router.register('database-app-permissions-system-users-relations', api.DatabaseAppPermissionSystemUserRelationViewSet, 'database-app-permissions-system-users-relation')

user_permission_urlpatterns = [
    path('<uuid:pk>/database-apps/', api.UserGrantedDatabaseAppsApi.as_view(), name='user-database-apps'),
    path('database-apps/', api.UserGrantedDatabaseAppsApi.as_view(), name='my-database-apps'),

    # DatabaseApps as tree
    path('<uuid:pk>/database-apps/tree/', api.UserGrantedDatabaseAppsAsTreeApi.as_view(), name='user-databases-apps-tree'),
    path('database-apps/tree/', api.UserGrantedDatabaseAppsAsTreeApi.as_view(), name='my-databases-apps-tree'),

    path('<uuid:pk>/database-apps/<uuid:database_app_id>/system-users/', api.UserGrantedDatabaseAppSystemUsersApi.as_view(), name='user-database-app-system-users'),
    path('database-apps/<uuid:database_app_id>/system-users/', api.UserGrantedDatabaseAppSystemUsersApi.as_view(), name='user-database-app-system-users'),
]

user_group_permission_urlpatterns = [
    path('<uuid:pk>/database-apps/', api.UserGroupGrantedDatabaseAppsApi.as_view(), name='user-group-database-apps'),
]

permission_urlpatterns = [
    # 授权规则中授权的用户和数据库应用
    path('<uuid:pk>/users/all/', api.DatabaseAppPermissionAllUserListApi.as_view(), name='database-app-permission-all-users'),
    path('<uuid:pk>/database-apps/all/', api.DatabaseAppPermissionAllDatabaseAppListApi.as_view(), name='database-app-permission-all-database-apps'),

    # 验证用户是否有某个数据库应用的权限
    path('user/validate/', api.ValidateUserDatabaseAppPermissionApi.as_view(), name='validate-user-database-app-permission'),
]

database_app_permission_urlpatterns = [
    path('users/', include(user_permission_urlpatterns)),
    path('user-groups/', include(user_group_permission_urlpatterns)),
    path('database-app-permissions/', include(permission_urlpatterns))
]

database_app_permission_urlpatterns += router.urls
