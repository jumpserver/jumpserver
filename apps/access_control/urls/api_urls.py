from rest_framework_bulk.routes import BulkRouter

from access_control.api import LoginPolicyViewSet

app_name = 'access-control'

router = BulkRouter()
router.register('access-controls', LoginPolicyViewSet, 'access-control')

urlpatterns = router.urls
