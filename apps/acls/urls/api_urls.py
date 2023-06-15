from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = 'acls'

router = BulkRouter()
router.register(r'login-acls', api.LoginACLViewSet, 'login-acl')
router.register(r'login-asset-acls', api.LoginAssetACLViewSet, 'login-asset-acl')
router.register(r'command-filter-acls', api.CommandFilterACLViewSet, 'command-filter-acl')
router.register(r'command-groups', api.CommandGroupViewSet, 'command-group')
router.register(r'connect-method-acls', api.ConnectMethodACLViewSet, 'connect-method-acl')

urlpatterns = [
    path('login-asset/check/', api.LoginAssetCheckAPI.as_view(), name='login-asset-check'),
]

urlpatterns += router.urls
