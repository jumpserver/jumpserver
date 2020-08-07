# coding: utf-8
#

from django.urls import path, include
from rest_framework_bulk.routes import BulkRouter
from .. import api


router = BulkRouter()
router.register('k8s-app-permissions', api.K8sAppPermissionViewSet, 'k8s-app-permission')
router.register('k8s-app-permissions-users-relations', api.K8sAppPermissionUserRelationViewSet, 'k8s-app-permissions-users-relation')
router.register('k8s-app-permissions-user-groups-relations', api.K8sAppPermissionUserGroupRelationViewSet, 'k8s-app-permissions-user-groups-relation')
router.register('k8s-app-permissions-k8s-apps-relations', api.K8sAppPermissionK8sAppRelationViewSet, 'k8s-app-permissions-k8s-apps-relation')
router.register('k8s-app-permissions-system-users-relations', api.K8sAppPermissionSystemUserRelationViewSet, 'k8s-app-permissions-system-users-relation')

user_permission_urlpatterns = [
    path('<uuid:pk>/k8s-apps/', api.UserGrantedK8sAppsApi.as_view(), name='user-k8s-apps'),
    path('k8s-apps/', api.UserGrantedK8sAppsApi.as_view(), name='my-k8s-apps'),

    # k8sApps as tree
    path('<uuid:pk>/k8s-apps/tree/', api.UserGrantedK8sAppsAsTreeApi.as_view(), name='user-k8ss-apps-tree'),
    path('k8s-apps/tree/', api.UserGrantedK8sAppsAsTreeApi.as_view(), name='my-k8ss-apps-tree'),

    path('<uuid:pk>/k8s-apps/<uuid:k8s_app_id>/system-users/', api.UserGrantedK8sAppSystemUsersApi.as_view(), name='user-k8s-app-system-users'),
    path('k8s-apps/<uuid:k8s_app_id>/system-users/', api.UserGrantedK8sAppSystemUsersApi.as_view(), name='user-k8s-app-system-users'),
]

user_group_permission_urlpatterns = [
    path('<uuid:pk>/k8s-apps/', api.UserGroupGrantedK8sAppsApi.as_view(), name='user-group-k8s-apps'),
]

permission_urlpatterns = [
    path('<uuid:pk>/users/all/', api.K8sAppPermissionAllUserListApi.as_view(), name='k8s-app-permission-all-users'),
    path('<uuid:pk>/k8s-apps/all/', api.K8sAppPermissionAllK8sAppListApi.as_view(), name='k8s-app-permission-all-k8s-apps'),

    path('user/validate/', api.ValidateUserK8sAppPermissionApi.as_view(), name='validate-user-k8s-app-permission'),
]

k8s_app_permission_urlpatterns = [
    path('users/', include(user_permission_urlpatterns)),
    path('user-groups/', include(user_group_permission_urlpatterns)),
    path('k8s-app-permissions/', include(permission_urlpatterns))
]

k8s_app_permission_urlpatterns += router.urls
