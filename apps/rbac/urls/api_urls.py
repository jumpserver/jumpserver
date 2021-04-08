from rest_framework_bulk.routes import BulkRouter
from .. import api

app_name = 'rbac'


router = BulkRouter()


router.register(r'roles', api.RoleViewSet, basename='role')
router.register(r'safe-role-binding', api.SafeRoleBindingViewSet, basename='role-binding')
router.register(r'permissions', api.PermissionsViewSet, basename='permission')
router.register(r'content-type', api.ContentTypeViewSet, basename='content-type')

urlpatterns = router.urls
