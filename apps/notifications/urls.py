
from rest_framework_bulk.routes import BulkRouter

from . import api

app_name = 'notifications'

router = BulkRouter()
router.register('backends', api.BackendViewSet, 'backend')
router.register('messages', api.MessageViewSet, 'message')

urlpatterns = router.urls
