
from rest_framework_bulk.routes import BulkRouter
from django.urls import path

from notifications import api

app_name = 'notifications'

router = BulkRouter()
router.register('system-msg-subscription', api.SystemMsgSubscriptionViewSet, 'system-msg-subscription')
router.register('site-message', api.SiteMessageViewSet, 'site-message')

urlpatterns = [
    path('backends/', api.BackendListView.as_view(), name='backends')
] + router.urls
