from django.db.models import Count, Max, Q
from django.utils import translation
from rest_framework import mixins
from rest_framework.response import Response

from audits.const import ActionChoices
from audits.handler import create_or_update_operate_log
from common.api import JMSGenericViewSet
from orgs.utils import current_org
from rbac.permissions import RBACPermission

from chat_ai.filters import ConversationAuditFilterSet
from chat_ai.models import AuditConversation
from chat_ai.serializers import AuditConversationDetailSerializer, AuditConversationSerializer


class ConversationAuditViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, JMSGenericViewSet):
    permission_classes = (RBACPermission,)
    http_method_names = ('get', 'head', 'options')
    filterset_class = ConversationAuditFilterSet
    search_fields = ('title', 'subject_name', 'subject_username')
    ordering_fields = ('date_created', 'date_updated', 'title')
    ordering = ('-date_updated', '-id')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AuditConversationDetailSerializer
        return AuditConversationSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return AuditConversation.objects.none()
        queryset = AuditConversation.objects.filter(org_id=str(current_org.id)).annotate(
            message_count=Count('messages'),
            question_count=Count('messages', filter=Q(messages__role='user')),
            last_question_at=Max('messages__date_created', filter=Q(messages__role='user')),
        ).filter(question_count__gt=0)
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('messages')
        return queryset

    def retrieve(self, request, *args, **kwargs):
        conversation = self.get_object()
        with translation.override('en'):
            create_or_update_operate_log(
                ActionChoices.view, 'Chat AI conversation audit', resource=conversation,
                resource_display=(conversation.title or str(conversation.id))[:128],
                force=True,
                after={
                    'Conversation owner': str(conversation.subject_id),
                    'Conversation ID': str(conversation.id),
                },
            )
        return Response(self.get_serializer(conversation).data)
