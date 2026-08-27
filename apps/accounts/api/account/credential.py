import time

from django.conf import settings
from django.db import transaction
from django.db.models import CharField, F, Q, TextField, Value
from django.db.models.functions import Cast, Coalesce
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from rest_framework import generics, serializers as drf_serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import serializers
from accounts.const import (
    CredentialIssueStatus, CredentialLeaseStatus,
    CredentialPolicyMode, CredentialPolicyStatus,
)
from accounts.credentials import CredentialError, CredentialPolicyService
from accounts.models import (
    AutomationExecution, CredentialIssueRequest, CredentialLease, CredentialPolicy,
    CredentialPolicyVersion,
)
from accounts.tasks import (
    cleanup_credential_issue_task, disable_credential_policy_task,
    issue_credential_task, revoke_credential_lease_task,
    rotate_credential_policy_task,
)
from audits.models import IntegrationApplicationLog
from authentication.backends.drf import CredentialServiceAuthentication
from common.const import Status
from common.permissions import IsValidUser
from common.utils import get_request_ip, is_uuid
from orgs.mixins.api import OrgBulkModelViewSet, OrgReadonlyModelViewSet
from rbac.permissions import RBACPermission


def credential_error_response(error):
    return Response(
        {'code': error.code, 'detail': error.detail},
        status=error.status_code,
    )


def no_store(response):
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response


class CredentialActivitySerializer(drf_serializers.Serializer):
    id = drf_serializers.UUIDField(read_only=True)
    policy_id = drf_serializers.UUIDField(read_only=True)
    policy_name = drf_serializers.CharField(read_only=True)
    event_type = drf_serializers.CharField(read_only=True)
    activity_status = drf_serializers.CharField(read_only=True)
    username = drf_serializers.CharField(
        read_only=True, allow_blank=True, allow_null=True,
    )
    date = drf_serializers.DateTimeField(read_only=True)
    detail = drf_serializers.CharField(read_only=True, allow_blank=True)
    value = drf_serializers.CharField(read_only=True, allow_blank=True)
    reason = drf_serializers.CharField(read_only=True, allow_blank=True)


class CredentialPolicyViewSet(OrgBulkModelViewSet):
    model = CredentialPolicy
    serializer_class = serializers.CredentialPolicySerializer
    permission_classes = [RBACPermission]
    filterset_fields = ('id', 'application', 'mode', 'status', 'asset')
    search_fields = ('name', 'comment')
    rbac_perms = {
        'rotate': 'accounts.change_credentialpolicy',
        'disable': 'accounts.change_credentialpolicy',
        'enable': 'accounts.change_credentialpolicy',
        'versions': 'accounts.view_credentialpolicyversion',
    }

    def perform_destroy(self, instance):
        if instance.status != CredentialPolicyStatus.disabled:
            raise drf_serializers.ValidationError(
                _('Disable the credential policy before deleting it')
            )
        if (
            instance.leases.filter(status__in=[
                CredentialLeaseStatus.active,
                CredentialLeaseStatus.revoking,
            ]).exists()
            or instance.leases.filter(account__isnull=False).exists()
        ):
            raise drf_serializers.ValidationError(
                _('Credential policy still has leases requiring cleanup')
            )
        if instance.issue_requests.filter(status__in=[
            CredentialIssueStatus.pending,
            CredentialIssueStatus.running,
            CredentialIssueStatus.cleaning,
        ]).exists():
            raise drf_serializers.ValidationError(
                _('Credential policy still has active issue requests')
            )
        return super().perform_destroy(instance)

    @action(['POST'], detail=True)
    def rotate(self, request, *args, **kwargs):
        policy = self.get_object()
        if policy.mode != CredentialPolicyMode.static:
            raise drf_serializers.ValidationError(
                _('Only rotating account policies can be rotated')
            )
        if policy.status not in (
            CredentialPolicyStatus.enabled,
            CredentialPolicyStatus.uncertain,
            CredentialPolicyStatus.disabled,
            CredentialPolicyStatus.rotating,
        ):
            raise drf_serializers.ValidationError(
                _('Credential policy is not enabled')
            )
        execution, __ = CredentialPolicyService.prepare_rotation(policy)
        task_id = None
        if execution and execution.status == Status.pending:
            try:
                result = rotate_credential_policy_task.apply_async(
                    args=[str(policy.id)],
                    kwargs={'execution_id': str(execution.id)},
                    task_id=str(execution.id),
                    priority=5,
                )
            except Exception:
                with transaction.atomic():
                    policy = CredentialPolicy.objects.select_for_update().get(
                        id=policy.id,
                    )
                    failed_execution = (
                        AutomationExecution.objects.select_for_update().get(
                            id=execution.id,
                        )
                    )
                    if (
                        policy.last_execution_id == failed_execution.id
                        and policy.status == CredentialPolicyStatus.rotating
                        and failed_execution.status == Status.pending
                    ):
                        failed_execution.status = Status.error
                        failed_execution.date_finished = timezone.now()
                        failed_execution.save(update_fields=[
                            'status', 'date_finished',
                        ])
                        snapshot = failed_execution.snapshot or {}
                        previous_status = snapshot.get(
                            'credential_policy_previous_status',
                            CredentialPolicyStatus.enabled,
                        )
                        policy.status = previous_status
                        previous_error = snapshot.get(
                            'credential_policy_previous_error',
                            '',
                        )
                        policy.last_error = (
                            previous_error
                            if previous_status != CredentialPolicyStatus.enabled
                            else previous_error or str(_(
                                'Credential rotation could not be scheduled'
                            ))
                        )
                        policy.save(update_fields=['status', 'last_error'])
                raise
            task_id = result.id
            CredentialPolicy.objects.filter(id=policy.id).update(
                operation_task_id=task_id,
            )
            policy.operation_task_id = task_id
        return Response({
            'task': task_id,
            'execution_id': execution.id if execution else None,
        }, status=status.HTTP_202_ACCEPTED)

    @action(['POST'], detail=True)
    def disable(self, request, *args, **kwargs):
        policy = self.get_object()
        if policy.status == CredentialPolicyStatus.disabled:
            return Response(self.get_serializer(policy).data)

        if (
            policy.mode == CredentialPolicyMode.static
            and policy.status != CredentialPolicyStatus.disabling
        ):
            disable_async = False
            with transaction.atomic():
                policy = CredentialPolicy.objects.select_for_update().get(
                    id=policy.id,
                )
                execution = policy.last_execution
                canceled_pending = False
                if execution and execution.status == Status.pending:
                    execution.status = Status.canceled
                    execution.date_finished = timezone.now()
                    execution.save(update_fields=['status', 'date_finished'])
                    snapshot = execution.snapshot or {}
                    previous_status = snapshot.get(
                        'credential_policy_previous_status',
                    )
                    policy.last_error = snapshot.get(
                        'credential_policy_previous_error',
                        policy.last_error,
                    )
                    if (
                        previous_status == CredentialPolicyStatus.uncertain
                        and not policy.last_error
                    ):
                        policy.last_error = str(_(
                            'Credential state is uncertain'
                        ))
                    canceled_pending = True
                if (
                    policy.status == CredentialPolicyStatus.rotating
                    and not canceled_pending
                ):
                    policy.status = CredentialPolicyStatus.disabling
                    disable_async = True
                else:
                    policy.status = CredentialPolicyStatus.disabled
                policy.save(update_fields=['status', 'last_error'])
            if not disable_async:
                return Response(self.get_serializer(policy).data)

        if policy.status != CredentialPolicyStatus.disabling:
            policy.status = CredentialPolicyStatus.disabling
            policy.save(update_fields=['status'])
        result = disable_credential_policy_task.apply_async(
            args=[str(policy.id)], priority=0,
        )
        CredentialPolicy.objects.filter(id=policy.id).update(
            operation_task_id=result.id,
        )
        policy.operation_task_id = result.id
        return Response(
            {'task': result.id, **self.get_serializer(policy).data},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(['POST'], detail=True)
    def enable(self, request, *args, **kwargs):
        policy_id = self.get_object().id
        with transaction.atomic():
            policy = CredentialPolicy.objects.select_for_update().select_related(
                'last_execution',
            ).get(id=policy_id)
            if policy.status == CredentialPolicyStatus.disabling:
                raise drf_serializers.ValidationError(
                    _('Credential policy is still being disabled')
                )
            if policy.status != CredentialPolicyStatus.disabled:
                return Response(self.get_serializer(policy).data)
            if (
                policy.mode == CredentialPolicyMode.static
                and policy.last_error
            ):
                raise drf_serializers.ValidationError(
                    _('Rotate the credential successfully before enabling the policy')
                )
            if (
                policy.mode == CredentialPolicyMode.static
                and policy.last_execution_id
                and not policy.last_execution.date_finished
            ):
                raise drf_serializers.ValidationError(
                    _('Credential rotation is not finished')
                )
            if policy.mode == CredentialPolicyMode.dynamic and (
                policy.leases.filter(status__in=[
                    CredentialLeaseStatus.active,
                    CredentialLeaseStatus.revoking,
                ]).exists()
                or policy.leases.filter(account__isnull=False).exists()
                or policy.issue_requests.filter(status__in=[
                    CredentialIssueStatus.pending,
                    CredentialIssueStatus.running,
                    CredentialIssueStatus.cleaning,
                ]).exists()
            ):
                raise drf_serializers.ValidationError(
                    _('Credential policy cleanup is not finished')
                )
            validator = self.get_serializer(policy, data={}, partial=True)
            validator.is_valid(raise_exception=True)
            policy.status = CredentialPolicyStatus.enabled
            policy.last_error = ''
            policy.save(update_fields=['status', 'last_error'])
        return Response(self.get_serializer(policy).data)

    @action(['GET'], detail=True)
    def versions(self, request, *args, **kwargs):
        policy = self.get_object()
        queryset = policy.versions.all()
        page = self.paginate_queryset(queryset)
        serializer = serializers.CredentialPolicyVersionSerializer(
            page if page is not None else queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class CredentialPolicyVersionViewSet(OrgReadonlyModelViewSet):
    model = CredentialPolicyVersion
    serializer_class = serializers.CredentialPolicyVersionSerializer
    permission_classes = [RBACPermission]
    filterset_fields = (
        'id', 'policy', 'policy__application', 'version', 'account',
    )


class CredentialIssueRequestViewSet(OrgReadonlyModelViewSet):
    model = CredentialIssueRequest
    serializer_class = serializers.CredentialIssueRequestSerializer
    permission_classes = [RBACPermission]
    filterset_fields = (
        'id', 'policy', 'policy__application', 'status', 'lease',
    )
    search_fields = ('username', 'error_code', 'error')


class CredentialActivityAPIView(generics.ListAPIView):
    serializer_class = CredentialActivitySerializer
    permission_classes = [RBACPermission]
    rbac_perms = {'GET': 'accounts.view_credentialpolicy'}

    fields = (
        'id', 'policy_id', 'policy_name', 'event_type',
        'activity_status', 'username', 'date', 'detail', 'value', 'reason',
    )

    @staticmethod
    def empty_text():
        return Value('', output_field=CharField())

    def get_queryset(self):
        application_id = self.request.query_params.get('application')
        if not is_uuid(application_id):
            raise drf_serializers.ValidationError({
                'application': _('A valid application is required'),
            })

        empty_text = self.empty_text()
        querysets = []
        if self.request.user.has_perm('accounts.view_credentialpolicyversion'):
            querysets.append(CredentialPolicyVersion.objects.filter(
                policy__application_id=application_id,
            ).annotate(
                policy_name=F('policy__name'),
                event_type=Value('rotation', output_field=CharField()),
                activity_status=Value('succeeded', output_field=CharField()),
                username=F('account__username'),
                date=F('date_created'),
                detail=Value('', output_field=TextField()),
                value=Cast('version', output_field=CharField()),
                reason=empty_text,
            ).values(*self.fields))

        if self.request.user.has_perm('accounts.view_credentialissuerequest'):
            querysets.append(CredentialIssueRequest.objects.filter(
                policy__application_id=application_id,
            ).annotate(
                policy_name=F('policy__name'),
                event_type=Value('issue', output_field=CharField()),
                activity_status=F('status'),
                date=Coalesce('date_completed', 'date_created'),
                detail=F('error'),
                value=empty_text,
                reason=empty_text,
            ).values(*self.fields))

        if self.request.user.has_perm('accounts.view_credentiallease'):
            leases = CredentialLease.objects.filter(
                policy__application_id=application_id,
            )
            querysets.append(leases.filter(
                date_last_renewed__isnull=False,
            ).annotate(
                policy_name=F('policy__name'),
                event_type=Value('renew', output_field=CharField()),
                activity_status=Value('succeeded', output_field=CharField()),
                date=F('date_last_renewed'),
                detail=Value('', output_field=TextField()),
                value=Cast('renew_count', output_field=CharField()),
                reason=empty_text,
            ).values(*self.fields))
            querysets.append(leases.filter(
                Q(date_revoked__isnull=False)
                | Q(status=CredentialLeaseStatus.revoking),
            ).annotate(
                policy_name=F('policy__name'),
                event_type=Value('revoke', output_field=CharField()),
                activity_status=F('status'),
                date=Coalesce('date_revoked', 'date_updated'),
                detail=F('revoke_error'),
                value=empty_text,
                reason=F('revoke_reason'),
            ).values(*self.fields))

        if not querysets:
            return CredentialPolicy.objects.none().values('id')
        return querysets[0].union(*querysets[1:]).order_by('-date')


class CredentialLeaseViewSet(OrgReadonlyModelViewSet):
    model = CredentialLease
    serializer_class = serializers.CredentialLeaseSerializer
    permission_classes = [RBACPermission]
    http_method_names = ['get', 'post', 'head', 'options']
    filterset_fields = (
        'id', 'policy', 'policy__application', 'status', 'account',
    )
    search_fields = ('username',)
    rbac_perms = {
        'renew': 'accounts.change_credentiallease',
        'revoke': 'accounts.change_credentiallease',
    }

    def create(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)

    @action(['POST'], detail=True)
    def renew(self, request, *args, **kwargs):
        lease = self.get_object()
        serializer = serializers.CredentialLeaseRenewSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        try:
            lease = CredentialPolicyService.renew(
                lease, serializer.validated_data.get('increment'),
            )
        except CredentialError as error:
            if error.code == 'LEASE_NOT_ACTIVE':
                revoke_credential_lease_task.apply_async(
                    args=[str(lease.id)], kwargs={'reason': 'expired'},
                    priority=2,
                )
            return credential_error_response(error)
        return Response(self.get_serializer(lease).data)

    @action(['POST'], detail=True)
    def revoke(self, request, *args, **kwargs):
        lease = self.get_object()
        if lease.status == CredentialLeaseStatus.active:
            lease.status = CredentialLeaseStatus.revoking
            lease.revoke_reason = 'admin'
            lease.save(update_fields=['status', 'revoke_reason'])
            result = revoke_credential_lease_task.apply_async(
                args=[str(lease.id)], kwargs={'reason': 'admin'}, priority=0,
            )
            return Response(
                {'task': result.id, **self.get_serializer(lease).data},
                status=status.HTTP_202_ACCEPTED,
            )
        if lease.status == CredentialLeaseStatus.revoking:
            result = revoke_credential_lease_task.apply_async(
                args=[str(lease.id)],
                kwargs={'reason': lease.revoke_reason or 'admin'}, priority=0,
            )
            return Response(
                {'task': result.id, **self.get_serializer(lease).data},
                status=status.HTTP_202_ACCEPTED,
            )
        return Response(self.get_serializer(lease).data)


@method_decorator(never_cache, name='dispatch')
class CredentialServiceAPIView(APIView):
    authentication_classes = [CredentialServiceAuthentication]
    permission_classes = [IsValidUser]

    def get_policy(self, policy_id):
        return CredentialPolicy.objects.select_related(
            'application', 'asset', 'account', 'management_account',
            'account_template',
        ).filter(
            id=policy_id,
            application=self.request.user,
            org_id=self.request.user.org_id,
        ).first()

    def get_lease(self, lease_id):
        return CredentialLease.objects.select_related(
            'policy__application', 'account',
        ).filter(
            id=lease_id,
            policy__application=self.request.user,
            org_id=self.request.user.org_id,
        ).first()

    @staticmethod
    def ensure_secret_readable():
        if settings.SECURITY_DISABLE_VIEW_SECRET:
            raise CredentialError(
                'SECRET_VIEW_DISABLED',
                _('Viewing credential secrets is disabled'), 403,
            )

    @staticmethod
    def ensure_enabled(policy):
        if policy.status == CredentialPolicyStatus.uncertain:
            raise CredentialError(
                'CREDENTIAL_UNAVAILABLE',
                _('Credential state is uncertain'), 503,
            )
        if policy.status == CredentialPolicyStatus.rotating:
            raise CredentialError(
                'CREDENTIAL_ROTATING',
                _('Credential is being rotated'), 503,
            )
        if policy.status != CredentialPolicyStatus.enabled:
            raise CredentialError(
                'CREDENTIAL_POLICY_DISABLED',
                _('Credential policy is not enabled'), 403,
            )

    @staticmethod
    def read_account_secret(account):
        try:
            secret = account.secret
        except Exception as error:
            raise CredentialError(
                'CREDENTIAL_UNAVAILABLE', _('Credential is unavailable'), 503,
            ) from error
        if not secret:
            raise CredentialError(
                'CREDENTIAL_UNAVAILABLE', _('Credential is unavailable'), 503,
            )
        return secret

    def log_read(self, account, asset=None):
        asset = asset or account.asset
        application = self.request.user
        IntegrationApplicationLog.objects.create(
            remote_addr=get_request_ip(self.request),
            service=application.name,
            service_id=application.id,
            account=f'{account.name}({account.username})',
            asset=f'{asset.name}({asset.address})',
        )


class CredentialServiceStaticAPI(CredentialServiceAPIView):
    def get(self, request, policy_id):
        try:
            self.ensure_secret_readable()
            policy = self.get_policy(policy_id)
            if not policy:
                return no_store(Response(status=status.HTTP_404_NOT_FOUND))
            if policy.mode != CredentialPolicyMode.static:
                raise CredentialError(
                    'INVALID_POLICY_MODE',
                    _('Policy does not provide a rotating credential'), 409,
                )
            self.ensure_enabled(policy)
            account = policy.account
            if not account or not account.is_active or not policy.asset.is_active:
                raise CredentialError(
                    'CREDENTIAL_UNAVAILABLE', _('Credential is unavailable'), 503,
                )
            secret = self.read_account_secret(account)
        except CredentialError as error:
            return no_store(credential_error_response(error))

        etag = (
            f'"credential-policy-{policy.id}-v{policy.current_version}'
            f'-a{account.version}"'
        )
        if request.headers.get('If-None-Match') == etag:
            response = Response(status=status.HTTP_304_NOT_MODIFIED)
            response['ETag'] = etag
            return no_store(response)

        try:
            next_rotation_at = policy.get_next_run_time()
        except (AttributeError, ValueError):
            next_rotation_at = None
        self.log_read(account, policy.asset)
        response = Response({
            'policy_id': policy.id,
            'version': policy.current_version,
            'account_version': account.version,
            'account_id': account.id,
            'username': account.username,
            'secret_type': account.secret_type,
            'secret': secret,
            'rotated_at': policy.date_last_rotated,
            'next_rotation_at': next_rotation_at,
        })
        response['ETag'] = etag
        return no_store(response)


class CredentialServiceIssueAPI(CredentialServiceAPIView):
    wait_timeout = 30

    @staticmethod
    def issue_response(issue, response_status=status.HTTP_201_CREATED):
        lease = issue.lease
        account = lease.account if lease else None
        if not issue.replayable or not account \
                or lease.status != CredentialLeaseStatus.active \
                or lease.date_expires <= timezone.now():
            return credential_error_response(CredentialError(
                'IDEMPOTENCY_REPLAY_EXPIRED',
                _('Credential response is no longer available'), 409,
            ))
        try:
            secret = CredentialServiceAPIView.read_account_secret(account)
        except CredentialError as error:
            return credential_error_response(error)
        return Response({
            'request_id': issue.id,
            'lease_id': lease.id,
            'ttl': max(0, int(
                (lease.date_expires - timezone.now()).total_seconds()
            )),
            'renewable': lease.renewable,
            'expires_at': lease.date_expires,
            'max_expires_at': lease.date_max_expires,
            'account_id': account.id,
            'username': account.username,
            'secret_type': account.secret_type,
            'secret': secret,
        }, status=response_status)

    def post(self, request, policy_id):
        try:
            self.ensure_secret_readable()
            if request.data:
                raise CredentialError(
                    'UNSUPPORTED_REQUEST_BODY',
                    _('Credential issue request does not accept a body'),
                )
            policy = self.get_policy(policy_id)
            if not policy:
                return no_store(Response(status=status.HTTP_404_NOT_FOUND))
            self.ensure_enabled(policy)
            if policy.mode != CredentialPolicyMode.dynamic:
                raise CredentialError(
                    'INVALID_POLICY_MODE',
                    _('Policy does not issue temporary credentials'), 409,
                )
            idempotency_key = request.headers.get('Idempotency-Key')
            if idempotency_key and len(idempotency_key) > 128:
                raise CredentialError(
                    'INVALID_IDEMPOTENCY_KEY',
                    _('Idempotency key is too long'),
                )
            issue, created = CredentialPolicyService.create_issue_request(
                policy,
                idempotency_key=idempotency_key,
                remote_addr=get_request_ip(request),
                timeout=self.wait_timeout,
            )
        except CredentialError as error:
            return no_store(credential_error_response(error))

        if created or (
            issue.status == CredentialIssueStatus.pending
            and not issue.execution_id
        ):
            issue_credential_task.apply_async(
                args=[str(issue.id)], priority=5, expires=issue.deadline,
            )

        deadline = time.monotonic() + self.wait_timeout
        while time.monotonic() < deadline:
            issue.refresh_from_db()
            if issue.status not in (
                CredentialIssueStatus.pending,
                CredentialIssueStatus.running,
                CredentialIssueStatus.cleaning,
            ):
                break
            time.sleep(0.2)

        issue.refresh_from_db()
        if issue.status == CredentialIssueStatus.succeeded:
            policy.refresh_from_db(fields=['status'])
            try:
                self.ensure_enabled(policy)
            except CredentialError as error:
                return no_store(credential_error_response(error))
            response = self.issue_response(
                issue,
                status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
            if response.status_code < 400 and issue.lease.account:
                self.log_read(issue.lease.account)
            return no_store(response)

        if issue.status in (
            CredentialIssueStatus.pending,
            CredentialIssueStatus.running,
            CredentialIssueStatus.cleaning,
        ):
            updated = CredentialIssueRequest.objects.filter(
                id=issue.id,
                status__in=[
                    CredentialIssueStatus.pending,
                    CredentialIssueStatus.running,
                ],
            ).update(
                status=CredentialIssueStatus.cleaning,
                error_code='CREDENTIAL_ISSUE_TIMEOUT',
                error=str(_('Credential issue timed out')),
            )
            if updated:
                cleanup_credential_issue_task.apply_async(
                    args=[str(issue.id)], priority=0,
                )
                error = CredentialError(
                    'CREDENTIAL_ISSUE_TIMEOUT',
                    _('Credential issue timed out'), 504,
                )
                return no_store(credential_error_response(error))

            issue.refresh_from_db()
            if issue.status == CredentialIssueStatus.succeeded:
                policy.refresh_from_db(fields=['status'])
                try:
                    self.ensure_enabled(policy)
                except CredentialError as error:
                    return no_store(credential_error_response(error))
                response = self.issue_response(
                    issue,
                    status.HTTP_201_CREATED if created else status.HTTP_200_OK,
                )
                if response.status_code < 400 and issue.lease.account:
                    self.log_read(issue.lease.account)
                return no_store(response)

        error = CredentialError(
            issue.error_code or 'CREDENTIAL_ISSUE_FAILED',
            issue.error or _('Credential issue failed'),
            504 if issue.status in (
                CredentialIssueStatus.cleaning,
                CredentialIssueStatus.timed_out,
            ) else 502,
        )
        return no_store(credential_error_response(error))


class CredentialServiceLeaseAPI(CredentialServiceAPIView):
    def get(self, request, lease_id):
        lease = self.get_lease(lease_id)
        if not lease:
            return no_store(Response(status=status.HTTP_404_NOT_FOUND))
        return no_store(Response(
            serializers.CredentialLeaseSerializer(lease).data
        ))

    def delete(self, request, lease_id):
        lease = self.get_lease(lease_id)
        if not lease:
            return no_store(Response(status=status.HTTP_404_NOT_FOUND))
        if lease.status == CredentialLeaseStatus.active:
            lease.status = CredentialLeaseStatus.revoking
            lease.revoke_reason = 'application'
            lease.save(update_fields=['status', 'revoke_reason'])
            result = revoke_credential_lease_task.apply_async(
                args=[str(lease.id)],
                kwargs={'reason': 'application'},
                priority=0,
            )
            return no_store(Response(
                {'task': result.id, 'lease_id': lease.id, 'status': lease.status},
                status=status.HTTP_202_ACCEPTED,
            ))
        if lease.status == CredentialLeaseStatus.revoking:
            result = revoke_credential_lease_task.apply_async(
                args=[str(lease.id)],
                kwargs={'reason': lease.revoke_reason or 'application'},
                priority=0,
            )
            return no_store(Response({
                'task': result.id,
                'lease_id': lease.id,
                'status': lease.status,
            }, status=status.HTTP_202_ACCEPTED))
        return no_store(Response(status=status.HTTP_204_NO_CONTENT))


class CredentialServiceLeaseRenewAPI(CredentialServiceAPIView):
    def post(self, request, lease_id):
        lease = self.get_lease(lease_id)
        if not lease:
            return no_store(Response(status=status.HTTP_404_NOT_FOUND))
        serializer = serializers.CredentialLeaseRenewSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        try:
            lease = CredentialPolicyService.renew(
                lease, serializer.validated_data.get('increment'),
            )
        except CredentialError as error:
            if error.code == 'LEASE_NOT_ACTIVE':
                revoke_credential_lease_task.apply_async(
                    args=[str(lease.id)], kwargs={'reason': 'expired'},
                    priority=2,
                )
            return no_store(credential_error_response(error))
        return no_store(Response(
            serializers.CredentialLeaseSerializer(lease).data
        ))
