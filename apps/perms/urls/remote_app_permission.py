# coding:utf-8

from django.urls import path
from rest_framework_bulk.routes import BulkRouter
from .. import api


router = BulkRouter()
router.register('remote-app-permissions', api.RemoteAppPermissionViewSet, 'remote-app-permission')
router.register('remote-app-permissions-users-relations', api.RemoteAppPermissionUserRelationViewSet, 'remote-app-permissions-users-relation')
router.register('remote-app-permissions-remote-apps-relations', api.RemoteAppPermissionRemoteAppRelationViewSet, 'remote-app-permissions-remote-apps-relation')


remote_app_permission_urlpatterns = [
    # 查询用户授权的RemoteApp
    path('users/<uuid:pk>/remote-apps/', api.UserGrantedRemoteAppsApi.as_view(), name='user-remote-apps'),
    path('users/remote-apps/', api.UserGrantedRemoteAppsApi.as_view(), name='my-remote-apps'),

    # 获取用户授权的RemoteApp树
    path('users/<uuid:pk>/remote-apps/tree/', api.UserGrantedRemoteAppsAsTreeApi.as_view(), name='user-remote-apps-as-tree'),
    path('users/remote-apps/tree/', api.UserGrantedRemoteAppsAsTreeApi.as_view(), name='my-remote-apps-as-tree'),

    # 查询用户组授权的RemoteApp
    path('user-groups/<uuid:pk>/remote-apps/', api.UserGroupGrantedRemoteAppsApi.as_view(), name='user-group-remote-apps'),

    # RemoteApp System users
    path('users/<uuid:pk>/remote-apps/<uuid:remote_app_id>/system-users/', api.UserGrantedRemoteAppSystemUsersApi.as_view(), name='user-remote-app-system-users'),
    path('users/remote-apps/<uuid:remote_app_id>/system-users/', api.UserGrantedRemoteAppSystemUsersApi.as_view(), name='my-remote-app-system-users'),

    # 校验用户对RemoteApp的权限
    path('remote-app-permissions/user/validate/', api.ValidateUserRemoteAppPermissionApi.as_view(), name='validate-user-remote-app-permission'),

    # 用户和RemoteApp变更
    path('remote-app-permissions/<uuid:pk>/users/add/', api.RemoteAppPermissionAddUserApi.as_view(), name='remote-app-permission-add-user'),
    path('remote-app-permissions/<uuid:pk>/users/remove/', api.RemoteAppPermissionRemoveUserApi.as_view(), name='remote-app-permission-remove-user'),
    path('remote-app-permissions/<uuid:pk>/remote-apps/remove/', api.RemoteAppPermissionRemoveRemoteAppApi.as_view(), name='remote-app-permission-remove-remote-app'),
    path('remote-app-permissions/<uuid:pk>/remote-apps/add/', api.RemoteAppPermissionAddRemoteAppApi.as_view(), name='remote-app-permission-add-remote-app'),

    path('remote-app-permissions/<uuid:pk>/remote-apps/all/', api.RemoteAppPermissionAllRemoteAppListApi.as_view(), name='remote-app-permission-all-remote-apps'),
    path('remote-app-permissions/<uuid:pk>/users/all/', api.RemoteAppPermissionAllUserListApi.as_view(), name='remote-app-permission-all-users'),
]

remote_app_permission_urlpatterns += router.urls
