from django.db.models import Count, Max, Prefetch, Q
from django.utils import translation
from rest_framework import mixins
from rest_framework.response import Response

from audits.const import ActionChoices
from audits.handler import create_or_update_operate_log
from common.api import JMSGenericViewSet
from common.permissions import OnlySuperUser
from orgs.utils import current_org

from chat_ai.models import Conversation, Message
from chat_ai.permissions import ChatAIServicePermission

from .serializers import (
    ConversationAuditDetailSerializer, ConversationAuditListSerializer,
)


class ConversationAuditViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    JMSGenericViewSet,
):
    permission_classes = (ChatAIServicePermission, OnlySuperUser)
    http_method_names = ('get', 'head', 'options')
    search_fields = ('title', 'user__name', 'user__username')
    ordering_fields = (
        'date_created', 'date_updated', 'title', 'message_count',
        'question_count', 'last_question_at',
    )
    ordering = ('-date_updated',)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConversationAuditDetailSerializer
        return ConversationAuditListSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Conversation.objects.none()

        queryset = Conversation.objects.filter(
            org_id=str(current_org.id),
        ).select_related('user').annotate(
            message_count=Count('messages'),
            question_count=Count(
                'messages',
                filter=Q(messages__role=Message.Role.USER),
            ),
            last_question_at=Max(
                'messages__date_created',
                filter=Q(messages__role=Message.Role.USER),
            ),
        )
        if self.action == 'retrieve':
            audit_messages = Message.objects.filter(
                role__in=(Message.Role.USER, Message.Role.ASSISTANT),
            ).prefetch_related('images', 'files')
            queryset = queryset.prefetch_related(
                Prefetch('messages', queryset=audit_messages, to_attr='audit_messages')
            )
        return queryset

    def retrieve(self, request, *args, **kwargs):
        conversation = self.get_object()
        response = Response(self.get_serializer(conversation).data)
        with translation.override('en'):
            create_or_update_operate_log(
                ActionChoices.view,
                'Chat AI conversation audit',
                resource=conversation,
                resource_display=(conversation.title or str(conversation.id))[:128],
                force=True,
                after={
                    'Conversation owner': str(conversation.user),
                    'Conversation ID': str(conversation.id),
                },
            )
        return response
