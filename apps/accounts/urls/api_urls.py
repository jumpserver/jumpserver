from rest_framework_bulk.routes import BulkRouter
from .. import api

app_name = 'accounts'

router = BulkRouter()

router.register(r'safes', api.SafeViewSet, basename='safe')


urlpatterns = router.urls
