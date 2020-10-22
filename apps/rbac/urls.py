from rbac import api
from rest_framework_bulk.routes import BulkRouter


app_name = 'rbac'
router = BulkRouter()
router.register(r'roles', api.RoleViewSet, 'role')
router.register(r'permissions', api.PermissionViewSet, 'permission')
router.register(r'role-namespaces', api.NamespaceRoleBindingViewSet, 'role-namespace')
router.register(r'role-orgs', api.OrgRoleBindingViewSet, 'role-org')

router.register(r'content-types', api.ContentTypeViewSet, 'content-type')

urlpatterns = [
]

urlpatterns += router.urls
