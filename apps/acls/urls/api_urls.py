from django.urls import path
from rest_framework_bulk.routes import BulkRouter
from .. import api


app_name = 'acls'


router = BulkRouter()
# router.register(r'login-acls', api, 'login-acl')
router.register(r'login-asset-acls', api.LoginAssetACLViewSet, 'login-asset-acl')

urlpatterns = []

urlpatterns += router.urls
