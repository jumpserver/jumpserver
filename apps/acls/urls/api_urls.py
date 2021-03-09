from django.urls import path
from rest_framework_bulk.routes import BulkRouter
from .. import api


app_name = 'acls'


router = BulkRouter()
router.register(r'login-acls', api.LoginACLViewSet, 'login-acl')
router.register(r'login-asset-acls', api.LoginAssetACLViewSet, 'login-asset-acl')

urlpatterns = [
    path('login-asset/check/', api.LoginAssetCheckAPI.as_view(), name='login-asset-check'),
    path('login-asset-confirm/<uuid:pk>/status/', api.LoginAssetConfirmStatusAPI.as_view(), name='login-asset-confirm-status')
]

urlpatterns += router.urls
