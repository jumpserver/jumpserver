from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .approval import ApprovalViewSet, OpenAPIRefreshViewSet
from .audit import ConversationAuditViewSet
from .conversation import ConversationViewSet
from .management import AssistantListView, ChatAIStatsView
from .transcription import TranscriptionView

app_name = 'chat_ai'

router = DefaultRouter()
router.register('conversations', ConversationViewSet, basename='conversation')
router.register('approvals', ApprovalViewSet, basename='approval')
router.register('openapi/refresh', OpenAPIRefreshViewSet, basename='openapi-refresh')
router.register('audit/conversations', ConversationAuditViewSet, basename='conversation-audit')

urlpatterns = [
    path('assistants/', AssistantListView.as_view(), name='assistant-list'),
    path('stats/', ChatAIStatsView.as_view(), name='stats'),
    path('transcriptions/', TranscriptionView.as_view(), name='transcription'),
    path('', include(router.urls)),
]
