from django.urls import path
from rest_framework_bulk.routes import BulkRouter
from .. import api

app_name = 'acls'

router = BulkRouter()
router.register(r'asset', api.AssetACLViewSet, 'asset')

urlpatterns = []

urlpatterns += router.urls
