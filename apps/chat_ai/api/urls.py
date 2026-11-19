from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .audit import ConversationAuditViewSet
from .runtime_store import RuntimeStoreView

app_name = 'chat_ai'

router = DefaultRouter()
router.register('audit/conversations', ConversationAuditViewSet, basename='conversation-audit')

urlpatterns = [
    path('runtime-store/', RuntimeStoreView.as_view(), name='runtime-store'),
    path('', include(router.urls)),
]
