
from rest_framework_bulk.routes import BulkRouter

from . import api

app_name = 'notifications'

router = BulkRouter()
router.register('subscriptions', api.SubscriptionViewSet, 'subscription')
router.register('backends', api.BackendViewSet, 'backend')
router.register('messages', api.MessageViewSet, 'message')
router.register('subscription-user-relations', api.SubscriptionUserRelationViewSet, 'subscription-user-relation')
router.register('subscription-group-relations', api.SubscriptionGroupRelationViewSet, 'subscription-group-relation')
router.register('subscription-message-relations', api.SubscriptionMessageRelationViewSet, 'subscription-message-relation')
router.register('subscription-backend-relations', api.SubscriptionBackendRelationViewSet, 'subscription-backend-relation')

urlpatterns = router.urls
