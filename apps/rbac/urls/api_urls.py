# coding:utf-8
from rest_framework_bulk.routes import BulkRouter
from rest_framework_nested import routers

from .. import api

app_name = 'rbac'


router = BulkRouter()
router.register(r'roles', api.RoleViewSet, 'role')
router.register(r'role-bindings', api.RoleBindingViewSet, 'role-binding')
router.register(r'permissions', api.PermissionViewSet, 'permission')

role_router = routers.NestedDefaultRouter(router, r'roles', lookup='role')
role_router.register(r'permissions', api.RolePermissionsViewSet, 'role-permission')

urlpatterns = []

urlpatterns += router.urls + role_router.urls
