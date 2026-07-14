import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api import JMSModelViewSet
from common.drf.throttling import RateThrottle
from common.permissions import IsValidUser, OnlySuperUser
from orgs.utils import current_org

from chat_ai.assistants import list_assistants
from chat_ai.models import AgentRun, ApiCallAudit, Message, ScheduledReport
from chat_ai.permissions import ChatAIOrgPermission, ChatAIServicePermission
from chat_ai.tasks import create_scheduled_report_run, run_scheduled_chat_ai_report
from chat_ai.throttling import (
    BackgroundTaskThrottle, enforce_background_enqueue_limits,
)

from .serializers import ScheduledReportSerializer


class BackgroundQueueUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Chat AI background queue is unavailable.'
    default_code = 'background_queue_unavailable'


class AssistantListView(APIView):
    permission_classes = (ChatAIServicePermission, IsValidUser, ChatAIOrgPermission)

    @extend_schema(responses={200: dict})
    def get(self, request):
        return Response({'results': list_assistants()})


class ScheduledReportViewSet(JMSModelViewSet):
    serializer_class = ScheduledReportSerializer
    permission_classes = (ChatAIServicePermission, IsValidUser, ChatAIOrgPermission)
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')
    search_fields = ('name', 'prompt')
    ordering_fields = ('name', 'date_created', 'date_updated', 'date_last_run')
    ordering = ('-date_updated',)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ScheduledReport.objects.none()
        return ScheduledReport.objects.filter(
            user=self.request.user,
            org_id=str(current_org.id),
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, org_id=str(current_org.id))

    @extend_schema(request=None, responses={202: dict})
    @action(
        methods=('post',), detail=True, url_path='run',
        throttle_classes=(RateThrottle, BackgroundTaskThrottle),
    )
    def run_now(self, request, pk=None):
        report = self.get_object()
        task_id = str(uuid.uuid4())
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            report = ScheduledReport.objects.select_for_update().get(pk=report.pk)
            if AgentRun.objects.filter(
                conversation__scheduled_report=report,
                status__in=(
                    AgentRun.Status.QUEUED,
                    AgentRun.Status.RUNNING,
                    AgentRun.Status.AWAITING_APPROVAL,
                ),
            ).exists():
                return Response(
                    {
                        'code': 'SCHEDULED_REPORT_BUSY',
                        'detail': 'This scheduled report is already queued or running.',
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            enforce_background_enqueue_limits(request.user.pk)
            run = create_scheduled_report_run(
                report,
                status=AgentRun.Status.QUEUED,
                task_id=task_id,
            )
        try:
            run_scheduled_chat_ai_report.apply_async(
                args=(str(report.id), str(run.id)),
                task_id=task_id,
            )
        except Exception as exc:
            now = timezone.now()
            AgentRun.objects.filter(
                pk=run.pk,
                status=AgentRun.Status.QUEUED,
            ).update(
                status=AgentRun.Status.FAILED,
                finished_at=now,
                error='BACKGROUND_QUEUE_UNAVAILABLE',
                date_updated=now,
            )
            Message.objects.filter(
                pk=run.assistant_message_id,
                status=Message.Status.PENDING,
            ).update(
                status=Message.Status.FAILED,
                error='BACKGROUND_QUEUE_UNAVAILABLE',
                date_updated=now,
            )
            raise BackgroundQueueUnavailable() from exc
        return Response(
            {
                'status': 'queued',
                'task_id': task_id,
                'agent_run_id': str(run.id),
                'conversation_id': str(run.conversation_id),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ChatAIStatsView(APIView):
    permission_classes = (ChatAIServicePermission, OnlySuperUser)

    @extend_schema(responses={200: dict})
    def get(self, request):
        try:
            days = min(365, max(1, int(request.query_params.get('days', 30))))
        except (TypeError, ValueError):
            days = 30
        since = timezone.now() - timedelta(days=days)
        org_id = str(current_org.id)
        runs = AgentRun.objects.filter(org_id=org_id, date_created__gte=since)
        usage = runs.aggregate(
            total=Count('id'),
            queued=Count('id', filter=Q(status=AgentRun.Status.QUEUED)),
            running=Count('id', filter=Q(status=AgentRun.Status.RUNNING)),
            completed=Count('id', filter=Q(status=AgentRun.Status.COMPLETED)),
            failed=Count('id', filter=Q(status=AgentRun.Status.FAILED)),
            cancelled=Count('id', filter=Q(status=AgentRun.Status.CANCELLED)),
            awaiting_approval=Count(
                'id', filter=Q(status=AgentRun.Status.AWAITING_APPROVAL)
            ),
            input_tokens=Sum('input_tokens'),
            output_tokens=Sum('output_tokens'),
            api_calls=Sum('api_call_count'),
            average_model_duration_ms=Avg('model_duration_ms'),
        )
        top_operations = list(
            ApiCallAudit.objects.filter(
                org_id=org_id, date_created__gte=since,
            ).values('operation_id').annotate(count=Count('id')).order_by('-count')[:10]
        )
        schedules = ScheduledReport.objects.filter(org_id=org_id).aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True, is_periodic=True)),
        )
        usage = {key: value or 0 for key, value in usage.items()}
        return Response({
            'days': days,
            'usage': usage,
            'top_operations': top_operations,
            'schedules': schedules,
        })
