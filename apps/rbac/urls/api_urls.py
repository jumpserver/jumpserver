from rest_framework_bulk.routes import BulkRouter
from .. import api

app_name = 'rbac'


router = BulkRouter()


router.register(r'roles', api.RoleViewSet, basename='role')
router.register(r'role-permissions', api.RolePermissionsViewSet, basename='role-permission')
router.register(r'safe-role-binding', api.SafeRoleBindingViewSet, basename='role-binding')

urlpatterns = router.urls
