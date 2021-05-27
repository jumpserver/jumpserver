
from rest_framework_bulk.routes import BulkRouter
from django.urls import path

from . import api

app_name = 'notifications'

router = BulkRouter()
router.register('system-msg-subscription', api.SystemMsgSubscriptionViewSet, 'system-msg-subscription')

urlpatterns = [
    path('backends/', api.BackendListView.as_view(), name='backends')
] + router.urls
