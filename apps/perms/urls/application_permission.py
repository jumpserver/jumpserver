# coding: utf-8
#

from django.urls import path, include
from rest_framework_bulk.routes import BulkRouter
from .. import api


router = BulkRouter()
router.register('application-permissions', api.ApplicationPermissionViewSet, 'application-permission')
router.register('application-permissions-users-relations', api.ApplicationPermissionUserRelationViewSet, 'application-permissions-users-relation')
router.register('application-permissions-user-groups-relations', api.ApplicationPermissionUserGroupRelationViewSet, 'application-permissions-user-groups-relation')
router.register('application-permissions-applications-relations', api.ApplicationPermissionApplicationRelationViewSet, 'application-permissions-application-relation')
router.register('application-permissions-system-users-relations', api.ApplicationPermissionSystemUserRelationViewSet, 'application-permissions-system-users-relation')

user_permission_urlpatterns = [
    path('<uuid:pk>/applications/', api.UserAllGrantedApplicationsApi.as_view(), name='user-applications'),
    path('applications/', api.MyAllGrantedApplicationsApi.as_view(), name='my-applications'),

    # Application As Tree
    path('<uuid:pk>/applications/tree/', api.UserAllGrantedApplicationsAsTreeApi.as_view(), name='user-applications-as-tree'),
    path('applications/tree/', api.MyAllGrantedApplicationsAsTreeApi.as_view(), name='my-applications-as-tree'),

    # Application System Users
    path('<uuid:pk>/applications/<uuid:application_id>/system-users/', api.UserGrantedApplicationSystemUsersApi.as_view(), name='user-application-system-users'),
    path('applications/<uuid:application_id>/system-users/', api.MyGrantedApplicationSystemUsersApi.as_view(), name='my-application-system-users'),
]

user_group_permission_urlpatterns = [
    path('<uuid:pk>/applications/', api.UserGroupGrantedApplicationsApi.as_view(), name='user-group-applications'),
]

permission_urlpatterns = [
    # 授权规则中授权的用户和应用
    path('<uuid:pk>/applications/all/', api.ApplicationPermissionAllApplicationListApi.as_view(), name='application-permission-all-applications'),
    path('<uuid:pk>/users/all/', api.ApplicationPermissionAllUserListApi.as_view(), name='application-permission-all-users'),

    # 验证用户是否有某个应用的权限
    path('user/validate/', api.ValidateUserApplicationPermissionApi.as_view(), name='validate-user-application-permission'),
]

application_permission_urlpatterns = [
    path('users/', include(user_permission_urlpatterns)),
    path('user-groups/', include(user_group_permission_urlpatterns)),
    path('application-permissions/', include(permission_urlpatterns))
]

application_permission_urlpatterns += router.urls
