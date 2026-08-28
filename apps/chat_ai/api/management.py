from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsValidUser, OnlySuperUser
from orgs.utils import current_org

from chat_ai.assistants import list_assistants
from chat_ai.models import AgentRun, ApiCallAudit
from chat_ai.permissions import CanUseChatAI, ChatAIOrgPermission, ChatAIServicePermission


class AssistantListView(APIView):
    permission_classes = (
        ChatAIServicePermission, IsValidUser, ChatAIOrgPermission, CanUseChatAI,
    )

    @extend_schema(responses={200: dict})
    def get(self, request):
        return Response({'results': list_assistants(request.user)})


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
        usage = {key: value or 0 for key, value in usage.items()}
        return Response({
            'days': days,
            'usage': usage,
            'top_operations': top_operations,
        })
