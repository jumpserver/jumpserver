import uuid
from copy import deepcopy

from celery import current_app
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import FileResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from common.api import JMSModelViewSet
from common.drf.throttling import RateThrottle
from common.permissions import IsValidUser
from common.utils import get_logger
from orgs.utils import current_org
from settings.models import get_chat_ai_config

from chat_ai.agents import AgentRunner
from chat_ai.agents.context import RequestAuthContext
from chat_ai.models import (
    AgentRun, Approval, Conversation, Message, MessageFile, MessageImage,
)
from chat_ai.permissions import CanUseChatAI, ChatAIOrgPermission, ChatAIServicePermission
from chat_ai.tasks import run_chat_ai_agent
from chat_ai.throttling import (
    BackgroundTaskThrottle, enforce_background_enqueue_limits,
)

from .serializers import (
    BackgroundMessageSerializer, BranchMessageSerializer, ConversationSerializer,
    MessageSerializer, RegenerateMessageSerializer, StreamMessageSerializer,
)


class EventStreamRenderer(JSONRenderer):
    media_type = 'text/event-stream'
    format = 'event-stream'


class BackgroundQueueUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Chat AI background queue is unavailable.'
    default_code = 'background_queue_unavailable'


logger = get_logger(__name__)


class ConversationViewSet(JMSModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = (
        ChatAIServicePermission, IsValidUser, ChatAIOrgPermission, CanUseChatAI,
    )
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')
    search_fields = ('title',)
    ordering_fields = ('date_created', 'date_updated', 'title')
    ordering = ('-date_updated',)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Conversation.objects.none()
        return Conversation.objects.filter(
            user=self.request.user, org_id=str(current_org.id)
        )

    def perform_create(self, serializer):
        model = get_chat_ai_config().get('model') or ''
        serializer.save(user=self.request.user, org_id=str(current_org.id), model=model)

    def destroy(self, request, *args, **kwargs):
        conversation = self.get_object()
        if conversation.agent_runs.filter(status__in=(
            AgentRun.Status.QUEUED,
            AgentRun.Status.RUNNING,
        )).exists():
            return Response(
                {
                    'code': 'CONVERSATION_BUSY',
                    'detail': 'Cancel the active generation before deleting this conversation.',
                },
                status=status.HTTP_409_CONFLICT,
            )
        conversation.approvals.filter(status=Approval.Status.PENDING).update(status=Approval.Status.CANCELLED)
        conversation.agent_runs.filter(status=AgentRun.Status.AWAITING_APPROVAL).update(
            status=AgentRun.Status.CANCELLED, finished_at=timezone.now()
        )
        return super().destroy(request, *args, **kwargs)

    @extend_schema(responses=MessageSerializer(many=True))
    @action(methods=('get',), detail=True, url_path='messages')
    def messages(self, request, pk=None):
        conversation = self.get_object()
        queryset = conversation.messages.prefetch_related('images', 'files').all()
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(MessageSerializer(page, many=True).data)
        return Response(MessageSerializer(queryset, many=True).data)

    @action(
        methods=('get',), detail=True,
        url_path=r'messages/(?P<message_id>[^/.]+)/images/(?P<image_id>[^/.]+)',
    )
    def message_image(self, request, pk=None, message_id=None, image_id=None):
        conversation = self.get_object()
        image = get_object_or_404(
            MessageImage,
            id=image_id,
            message_id=message_id,
            message__conversation=conversation,
        )
        response = FileResponse(
            image.file.open('rb'), content_type=image.content_type,
            as_attachment=False, filename=image.name,
        )
        response['Cache-Control'] = 'private, max-age=3600'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    @staticmethod
    def _busy_response():
        return Response(
            {
                'code': 'CONVERSATION_BUSY',
                'detail': 'Wait for or cancel the active generation before sending another message.',
            },
            status=status.HTTP_409_CONFLICT,
        )

    @staticmethod
    def _stream_response(runner):
        response = StreamingHttpResponse(
            runner.stream(), status=status.HTTP_200_OK,
            content_type='text/event-stream; charset=utf-8',
        )
        response['Cache-Control'] = 'no-cache, no-transform'
        response['X-Accel-Buffering'] = 'no'
        response['Connection'] = 'keep-alive'
        return response

    @staticmethod
    def _copy_message_attachments(source, target):
        for image in source.images.all():
            copied = MessageImage(
                message=target,
                name=image.name,
                content_type=image.content_type,
                size=image.size,
            )
            image.file.open('rb')
            try:
                copied.file.save(image.name, image.file, save=True)
            finally:
                image.file.close()
        for attachment in source.files.all():
            copied = MessageFile(
                message=target,
                name=attachment.name,
                content_type=attachment.content_type,
                size=attachment.size,
                extracted_text=attachment.extracted_text,
            )
            attachment.file.open('rb')
            try:
                copied.file.save(attachment.name, attachment.file, save=True)
            finally:
                attachment.file.close()

    def _copy_branch_history(self, source_conversation, target_message, branch):
        limit = getattr(settings, 'CHAT_AI_HISTORY_MESSAGES', 30)
        queryset = source_conversation.messages.filter(
            date_created__lt=target_message.date_created,
            status=Message.Status.COMPLETED,
            role__in=(Message.Role.USER, Message.Role.ASSISTANT, Message.Role.TOOL),
        ).prefetch_related('images', 'files').order_by('-date_created')[:limit]
        source_messages = list(reversed(list(queryset)))
        message_map = {}
        for source in source_messages:
            copied = Message.objects.create(
                conversation=branch,
                role=source.role,
                content=source.content,
                status=Message.Status.COMPLETED,
                model=source.model,
                input_tokens=source.input_tokens,
                output_tokens=source.output_tokens,
                result_cards=deepcopy(source.result_cards),
                web_search=source.web_search,
                regenerated_from=message_map.get(source.regenerated_from_id),
            )
            message_map[source.id] = copied
            self._copy_message_attachments(source, copied)

    @action(
        methods=('get',), detail=True,
        url_path=r'messages/(?P<message_id>[^/.]+)/files/(?P<file_id>[^/.]+)',
    )
    def message_file(self, request, pk=None, message_id=None, file_id=None):
        conversation = self.get_object()
        attachment = get_object_or_404(
            MessageFile,
            id=file_id,
            message_id=message_id,
            message__conversation=conversation,
        )
        response = FileResponse(
            attachment.file.open('rb'), content_type=attachment.content_type,
            as_attachment=True, filename=attachment.name,
        )
        response['Cache-Control'] = 'private, max-age=3600'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    @extend_schema(
        request=StreamMessageSerializer,
        responses={(200, 'text/event-stream'): OpenApiResponse(response=OpenApiTypes.STR, description='SSE stream')},
    )
    @action(
        methods=('post',), detail=True, url_path='messages/stream',
        renderer_classes=(EventStreamRenderer,),
        parser_classes=(JSONParser, MultiPartParser, FormParser),
    )
    def stream_message(self, request, pk=None):
        conversation = self.get_object()
        serializer = StreamMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data['content']
        images = serializer.validated_data.get('images', ())
        files = serializer.validated_data.get('files', ())
        web_search_enabled = serializer.validated_data.get('web_search', False)
        with transaction.atomic():
            # Serialize run creation for this conversation. The row lock keeps
            # concurrent workers from both observing an idle conversation.
            conversation = Conversation.objects.select_for_update().get(pk=conversation.pk)
            active_statuses = (
                AgentRun.Status.QUEUED,
                AgentRun.Status.RUNNING,
                AgentRun.Status.AWAITING_APPROVAL,
            )
            if conversation.agent_runs.filter(status__in=active_statuses).exists():
                return self._busy_response()
            if not conversation.title:
                fallback_title = files[0].name if files else 'Image'
                conversation.title = content.strip().replace('\n', ' ')[:80] or fallback_title
                conversation.save(update_fields=('title', 'date_updated'))
            user_message = Message.objects.create(
                conversation=conversation,
                role=Message.Role.USER,
                content=content,
                status=Message.Status.COMPLETED,
                web_search=web_search_enabled,
            )
            for uploaded in images:
                MessageImage.objects.create(
                    message=user_message,
                    file=uploaded,
                    name=uploaded.name,
                    content_type=uploaded.content_type,
                    size=uploaded.size,
                )
            for uploaded in files:
                MessageFile.objects.create(
                    message=user_message,
                    file=uploaded,
                    name=uploaded.name,
                    content_type=uploaded.content_type,
                    size=uploaded.size,
                    extracted_text=uploaded._chat_ai_extracted_text,
                )
            assistant_message = Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                status=Message.Status.STREAMING,
                model=conversation.model,
                web_search=web_search_enabled,
            )
            agent_run = AgentRun.objects.create(
                conversation=conversation,
                assistant_message=assistant_message,
                user=request.user,
                org_id=str(current_org.id),
                status=AgentRun.Status.RUNNING,
                started_at=timezone.now(),
            )
        auth_context = RequestAuthContext.from_request(request, current_org.id)
        runner = AgentRunner(
            conversation=conversation,
            user=request.user,
            user_message=user_message,
            assistant_message=assistant_message,
            agent_run=agent_run,
            auth_context=auth_context,
            web_search_enabled=web_search_enabled,
        )
        return self._stream_response(runner)

    @extend_schema(request=RegenerateMessageSerializer, responses={(200, 'text/event-stream'): str})
    @action(
        methods=('post',), detail=True,
        url_path=r'messages/(?P<message_id>[^/.]+)/regenerate',
        renderer_classes=(EventStreamRenderer,), parser_classes=(JSONParser,),
    )
    def regenerate_message(self, request, pk=None, message_id=None):
        conversation = self.get_object()
        serializer = RegenerateMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source_message = get_object_or_404(
            Message,
            id=message_id,
            conversation=conversation,
            role=Message.Role.ASSISTANT,
        )
        web_search_enabled = serializer.validated_data['web_search']
        with transaction.atomic():
            conversation = Conversation.objects.select_for_update().get(pk=conversation.pk)
            if conversation.agent_runs.filter(status__in=(
                AgentRun.Status.QUEUED, AgentRun.Status.RUNNING,
                AgentRun.Status.AWAITING_APPROVAL,
            )).exists():
                return self._busy_response()
            user_message = conversation.messages.filter(
                role=Message.Role.USER,
                date_created__lt=source_message.date_created,
            ).order_by('-date_created').first()
            if not user_message:
                raise ValidationError('The source user message no longer exists.')
            assistant_message = Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                status=Message.Status.STREAMING,
                model=conversation.model,
                web_search=web_search_enabled,
                regenerated_from=source_message,
            )
            agent_run = AgentRun.objects.create(
                conversation=conversation,
                assistant_message=assistant_message,
                user=request.user,
                org_id=str(current_org.id),
                status=AgentRun.Status.RUNNING,
                started_at=timezone.now(),
            )
        runner = AgentRunner(
            conversation=conversation,
            user=request.user,
            user_message=user_message,
            assistant_message=assistant_message,
            agent_run=agent_run,
            auth_context=RequestAuthContext.from_request(request, current_org.id),
            web_search_enabled=web_search_enabled,
        )
        return self._stream_response(runner)

    @extend_schema(request=BranchMessageSerializer, responses={(200, 'text/event-stream'): str})
    @action(
        methods=('post',), detail=True,
        url_path=r'messages/(?P<message_id>[^/.]+)/branch',
        renderer_classes=(EventStreamRenderer,), parser_classes=(JSONParser,),
    )
    def branch_message(self, request, pk=None, message_id=None):
        source_conversation = self.get_object()
        serializer = BranchMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data['content']
        source_message = get_object_or_404(
            Message.objects.prefetch_related('images', 'files'),
            id=message_id,
            conversation=source_conversation,
            role=Message.Role.USER,
            status=Message.Status.COMPLETED,
        )
        web_search_enabled = serializer.validated_data['web_search']
        if not content.strip() and not source_message.images.exists() and not source_message.files.exists():
            raise ValidationError('A branched message must include text or an attachment.')

        with transaction.atomic():
            source_conversation = Conversation.objects.select_for_update().get(
                pk=source_conversation.pk
            )
            if source_conversation.agent_runs.filter(status__in=(
                AgentRun.Status.QUEUED, AgentRun.Status.RUNNING,
                AgentRun.Status.AWAITING_APPROVAL,
            )).exists():
                return self._busy_response()
            title = content.strip().replace('\n', ' ')[:80] or source_message.content[:80]
            branch = Conversation.objects.create(
                user=request.user,
                org_id=str(current_org.id),
                title=title,
                model=source_conversation.model,
            )
            self._copy_branch_history(source_conversation, source_message, branch)
            user_message = Message.objects.create(
                conversation=branch,
                role=Message.Role.USER,
                content=content,
                status=Message.Status.COMPLETED,
                web_search=web_search_enabled,
            )
            self._copy_message_attachments(source_message, user_message)
            assistant_message = Message.objects.create(
                conversation=branch,
                role=Message.Role.ASSISTANT,
                status=Message.Status.STREAMING,
                model=branch.model,
                web_search=web_search_enabled,
            )
            agent_run = AgentRun.objects.create(
                conversation=branch,
                assistant_message=assistant_message,
                user=request.user,
                org_id=str(current_org.id),
                status=AgentRun.Status.RUNNING,
                started_at=timezone.now(),
            )
        runner = AgentRunner(
            conversation=branch,
            user=request.user,
            user_message=user_message,
            assistant_message=assistant_message,
            agent_run=agent_run,
            auth_context=RequestAuthContext.from_request(request, current_org.id),
            web_search_enabled=web_search_enabled,
        )
        response = self._stream_response(runner)
        response['X-Chat-AI-Conversation-ID'] = str(branch.id)
        return response

    @extend_schema(request=BackgroundMessageSerializer, responses={202: dict})
    @action(
        methods=('post',), detail=True, url_path='messages/background',
        parser_classes=(JSONParser,),
        throttle_classes=(RateThrottle, BackgroundTaskThrottle),
    )
    def background_message(self, request, pk=None):
        conversation = self.get_object()
        serializer = BackgroundMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data['content']
        web_search_enabled = serializer.validated_data['web_search']
        task_id = str(uuid.uuid4())
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            conversation = Conversation.objects.select_for_update().get(pk=conversation.pk)
            if conversation.agent_runs.filter(status__in=(
                AgentRun.Status.QUEUED, AgentRun.Status.RUNNING,
                AgentRun.Status.AWAITING_APPROVAL,
            )).exists():
                return self._busy_response()
            enforce_background_enqueue_limits(request.user.pk)
            if not conversation.title:
                conversation.title = content.strip().replace('\n', ' ')[:80]
                conversation.save(update_fields=('title', 'date_updated'))
            Message.objects.create(
                conversation=conversation,
                role=Message.Role.USER,
                content=content,
                status=Message.Status.COMPLETED,
                web_search=web_search_enabled,
            )
            assistant_message = Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                status=Message.Status.PENDING,
                model=conversation.model,
                web_search=web_search_enabled,
            )
            agent_run = AgentRun.objects.create(
                conversation=conversation,
                assistant_message=assistant_message,
                user=request.user,
                org_id=str(current_org.id),
                status=AgentRun.Status.QUEUED,
                task_id=task_id,
            )
        try:
            run_chat_ai_agent.apply_async(
                args=(
                    str(agent_run.id),
                    web_search_enabled,
                    False,
                    serializer.validated_data['notify'],
                ),
                task_id=task_id,
            )
        except Exception as exc:
            now = timezone.now()
            AgentRun.objects.filter(
                pk=agent_run.pk,
                status=AgentRun.Status.QUEUED,
            ).update(
                status=AgentRun.Status.FAILED,
                finished_at=now,
                error='BACKGROUND_QUEUE_UNAVAILABLE',
                date_updated=now,
            )
            Message.objects.filter(
                pk=assistant_message.pk,
                status=Message.Status.PENDING,
            ).update(
                status=Message.Status.FAILED,
                error='BACKGROUND_QUEUE_UNAVAILABLE',
                date_updated=now,
            )
            raise BackgroundQueueUnavailable() from exc
        return Response({
            'status': 'queued',
            'task_id': task_id,
            'agent_run_id': str(agent_run.id),
            'message_id': str(assistant_message.id),
        }, status=status.HTTP_202_ACCEPTED)

    @extend_schema(request=None, responses={202: OpenApiResponse(description='Cancellation requested')})
    @action(methods=('post',), detail=True, url_path='cancel')
    def cancel(self, request, pk=None):
        conversation = self.get_object()
        now = timezone.now()
        with transaction.atomic():
            runs = conversation.agent_runs.select_for_update().filter(
                user=request.user,
                status__in=(
                    AgentRun.Status.QUEUED,
                    AgentRun.Status.RUNNING,
                    AgentRun.Status.AWAITING_APPROVAL,
                ),
            )
            rows = list(runs.values_list('id', 'assistant_message_id', 'task_id'))
            run_ids = [run_id for run_id, _, _ in rows]
            message_ids = [message_id for _, message_id, _ in rows if message_id]
            task_ids = [task_id for _, _, task_id in rows if task_id]
            runs.update(
                status=AgentRun.Status.CANCELLED,
                finished_at=now,
                error='USER_CANCELLED',
                date_updated=now,
            )
            conversation.messages.filter(
                id__in=message_ids,
                status__in=(
                    Message.Status.PENDING,
                    Message.Status.STREAMING,
                    Message.Status.AWAITING_APPROVAL,
                ),
            ).update(
                status=Message.Status.CANCELLED,
                error='USER_CANCELLED',
                date_updated=now,
            )
            conversation.approvals.filter(
                status=Approval.Status.PENDING,
            ).update(status=Approval.Status.CANCELLED)
        cancel_timeout = max(
            60,
            getattr(settings, 'CHAT_AI_MODEL_TIMEOUT', 120)
            * getattr(settings, 'CHAT_AI_MAX_STEPS', 15),
        )
        for run_id in run_ids:
            try:
                cache.set(f'chat-ai:cancel:{run_id}', True, timeout=cancel_timeout)
            except Exception:
                logger.warning('Chat AI cancellation cache could not be updated: %s', run_id)
        for task_id in task_ids:
            try:
                current_app.control.revoke(task_id, terminate=False)
            except Exception:
                logger.warning('Chat AI Celery task could not be revoked: %s', task_id)
        return Response(
            {
                'status': 'cancelled',
                'agent_run_ids': run_ids,
                'task_ids': task_ids,
            },
            status=status.HTTP_202_ACCEPTED,
        )
