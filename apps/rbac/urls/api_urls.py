# coding:utf-8
from rest_framework_bulk.routes import BulkRouter
from rest_framework_nested import routers

from .. import api

app_name = 'rbac'

router = BulkRouter()
router.register(r'roles', api.RoleViewSet, 'role')
router.register(r'role-bindings', api.RoleBindingViewSet, 'role-binding')

router.register(r'system-roles', api.SystemRoleViewSet, 'system-role')
router.register(r'system-role-bindings', api.SystemRoleBindingViewSet, 'system-role-binding')

router.register(r'org-roles', api.OrgRoleViewSet, 'org-role')
router.register(r'org-role-bindings', api.OrgRoleBindingViewSet, 'org-role-binding')

router.register(r'permissions', api.PermissionViewSet, 'permission')
router.register(r'content-types', api.ContentTypeViewSet, 'content-type')

system_role_router = routers.NestedDefaultRouter(router, r'system-roles', lookup='system_role')
system_role_router.register(r'permissions', api.SystemRolePermissionsViewSet, 'system-role-permission')

org_role_router = routers.NestedDefaultRouter(router, r'org-roles', lookup='org_role')
org_role_router.register(r'permissions', api.OrgRolePermissionsViewSet, 'org-role-permission')

urlpatterns = []

urlpatterns += router.urls + system_role_router.urls + org_role_router.urls
