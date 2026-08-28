from asgiref.sync import async_to_sync
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.response import Response

from common.api import JMSGenericViewSet
from common.permissions import IsValidUser, OnlySuperUser
from orgs.utils import current_org

from chat_ai.agents.context import RequestAuthContext
from chat_ai.assistants import get_assistant, is_assistant_available
from chat_ai.approvals import ApprovalService
from chat_ai.executor.core_client import CoreAPIExecutor
from chat_ai.models import Approval
from chat_ai.openapi import OpenAPILoader
from chat_ai.permissions import CanUseChatAI, ChatAIOrgPermission, ChatAIServicePermission
from chat_ai.policies import PolicyEngine

from .serializers import ApprovalSerializer, OpenAPIRegistrySerializer


class CoreExecutionError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = 'Core API execution failed.'
    default_code = 'core_api_failed'


class ApprovalViewSet(mixins.RetrieveModelMixin, JMSGenericViewSet):
    serializer_class = ApprovalSerializer
    permission_classes = (
        ChatAIServicePermission, IsValidUser, ChatAIOrgPermission, CanUseChatAI,
    )
    http_method_names = ('get', 'post', 'head', 'options')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Approval.objects.none()
        return Approval.objects.filter(user=self.request.user, org_id=str(current_org.id))

    @extend_schema(request=None, responses=ApprovalSerializer)
    @action(methods=('post',), detail=True, url_path='confirm')
    def confirm(self, request, pk=None):
        approval_record = self.get_object()
        profile = get_assistant(
            approval_record.conversation.assistant if approval_record.conversation else None
        )
        if (
            not profile.core_api_enabled
            or not is_assistant_available(profile.key, request.user)
        ):
            raise PermissionDenied('Assistant is not available for this operation.')
        loader = OpenAPILoader()
        registry = async_to_sync(loader.load)()
        policy = PolicyEngine(
            operation_scope=profile.operation_ids,
            full_access=profile.full_access,
        )
        service = ApprovalService(registry, policy)
        approval, _ = service.prepare_confirmation(pk, request.user, current_org.id)
        auth_context = RequestAuthContext.from_request(request, current_org.id)
        executor = CoreAPIExecutor(registry, policy)
        try:
            result = async_to_sync(executor.execute)(
                approval.operation_id,
                approval.request_payload,
                auth_context,
                approval.agent_run,
                approval,
            )
        except Exception as exc:
            service.fail(approval, exc)
            raise CoreExecutionError() from exc
        service.finish(approval, result)
        approval.refresh_from_db()
        return Response({'approval': ApprovalSerializer(approval).data, 'result': result})

    @extend_schema(request=None, responses=ApprovalSerializer)
    @action(methods=('post',), detail=True, url_path='cancel')
    def cancel(self, request, pk=None):
        self.get_object()
        approval = ApprovalService.cancel(pk, request.user, current_org.id)
        return Response(ApprovalSerializer(approval).data)


class OpenAPIRefreshViewSet(mixins.CreateModelMixin, JMSGenericViewSet):
    permission_classes = (ChatAIServicePermission, OnlySuperUser)
    serializer_class = OpenAPIRegistrySerializer
    _ignore_rbac_permissions = True

    @extend_schema(request=None, responses=OpenAPIRegistrySerializer)
    def create(self, request, *args, **kwargs):
        loader = OpenAPILoader()
        registry = async_to_sync(loader.refresh)()
        return Response({
            'schema_hash': loader.schema_hash,
            'schema_version': loader.schema_version,
            'operation_count': len(registry),
            'refreshed_at': timezone.now(),
        })
