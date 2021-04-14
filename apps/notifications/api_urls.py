
from rest_framework_bulk.routes import BulkRouter

from . import api

app_name = 'notifications'

router = BulkRouter()
router.register('notifications', api.SubscriptionViewSet, 'notifications')

urlpatterns = router.urls
