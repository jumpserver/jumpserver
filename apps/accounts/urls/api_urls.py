from rest_framework_bulk.routes import BulkRouter
from .. import api

app_name = 'accounts'

router = BulkRouter()

router.register(r'safes', api.SafeViewSet, basename='safe')
router.register(r'account-types', api.AccountTypeViewSet, basename='account-type')
router.register(r'accounts', api.AccountViewSet, basename='account')


urlpatterns = router.urls
