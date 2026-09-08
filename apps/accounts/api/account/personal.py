from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from accounts.models import PersonalAssetCredential
from accounts.personal_credentials import (
    PERSONAL_CREDENTIAL_SECRET_TYPES,
    get_personal_credential_permission_context,
    record_personal_credential_audit,
    validate_personal_credential_secret_type,
    validate_personal_credential_test_acl,
    validate_personal_credential_verification_protocol,
)
from accounts.serializers import PersonalAssetCredentialSerializer
from accounts.tasks import verify_personal_credentials_task
from assets.const import Connectivity
from assets.models import Asset
from common.permissions import IsValidUser
from common.utils import get_logger, get_request_ip, is_uuid
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.models import Organization
from orgs.utils import current_org

logger = get_logger(__name__)


def user_can_access_current_org(user):
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_superuser
            or user.orgs.filter(id=current_org.id).exists()
        )
    )


class IsPersonalCredentialOrgMember(IsValidUser):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and user_can_access_current_org(request.user)
        )


class PersonalCredentialTestThrottle(UserRateThrottle):
    scope = 'personal_credential_test'
    rate = '3/min'

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        ident = '{}:{}'.format(request.user.pk, current_org.id)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident,
        }


class PersonalAssetCredentialViewSet(OrgBulkModelViewSet):
    model = PersonalAssetCredential
    serializer_class = PersonalAssetCredentialSerializer
    permission_classes = [IsPersonalCredentialOrgMember]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    filterset_fields = ('asset', 'protocol', 'secret_type', 'is_active', 'username')
    search_fields = ('username', 'asset__name', 'asset__address', 'comment')
    ordering_fields = ('username', 'date_created', 'date_updated')
    lookup_value_regex = (
        '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
        '[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
    )

    def get_queryset(self):
        return super().get_queryset().filter(
            owner=self.request.user,
            org_id=current_org.id,
        ).select_related('asset').defer('_secret')

    @action(
        methods=['post'], detail=True,
        throttle_classes=[PersonalCredentialTestThrottle],
    )
    def test(self, request, *args, **kwargs):
        credential = self.get_object()
        if not credential.is_active:
            raise ValidationError({
                'is_active': _('Inactive personal credentials cannot be tested')
            })
        platform_protocol, permission_account = (
            get_personal_credential_permission_context(
                request.user, credential.asset, credential.protocol
            )
        )
        validate_personal_credential_secret_type(
            platform_protocol, credential.secret_type
        )
        validate_personal_credential_verification_protocol(
            credential.asset, credential.protocol
        )
        remote_addr = get_request_ip(request)
        validate_personal_credential_test_acl(
            request.user,
            credential.asset,
            permission_account,
            credential.username,
            remote_addr,
        )
        PersonalAssetCredential.objects.filter(
            id=credential.id,
            owner=request.user,
            version=credential.version,
        ).update(connectivity=Connectivity.UNKNOWN, date_verified=None)
        try:
            task = verify_personal_credentials_task.delay(
                [str(credential.id)],
                str(request.user.id),
                str(credential.org_id),
                [str(credential.asset_id)],
                remote_addr,
                {str(credential.id): credential.version},
            )
        except Exception:
            PersonalAssetCredential.objects.filter(
                id=credential.id,
                owner=request.user,
                version=credential.version,
            ).update(
                connectivity=Connectivity.ERR,
                date_verified=timezone.now(),
            )
            record_personal_credential_audit(
                operation='test',
                result='failed',
                failure_reason='task_dispatch_failed',
                user=request.user,
                credential=credential,
                remote_addr=remote_addr,
            )
            raise
        try:
            record_personal_credential_audit(
                operation='test', result='requested', user=request.user,
                credential=credential, remote_addr=remote_addr,
            )
        except Exception as audit_error:
            logger.warning(
                'Record personal credential test request audit error: %s',
                audit_error,
            )
        return Response(
            {'task': task.id}, status=status.HTTP_202_ACCEPTED
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        record_personal_credential_audit(
            operation='create', result='success', user=self.request.user,
            credential=instance,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        record_personal_credential_audit(
            operation='update', result='success', user=self.request.user,
            credential=instance,
        )

    def perform_destroy(self, instance):
        metadata = {
            'credential_id': instance.id,
            'asset': instance.asset,
            'username': instance.username,
            'secret_type': instance.secret_type,
        }
        instance.delete()
        record_personal_credential_audit(
            operation='delete', result='success', user=self.request.user,
            **metadata,
        )

    def get_failure_audit_metadata(self):
        credential_id = self.kwargs.get(self.lookup_field)
        if not user_can_access_current_org(self.request.user):
            return {
                'credential_id': (
                    str(credential_id)
                    if credential_id and is_uuid(credential_id)
                    else None
                ),
                'org_id': Organization.DEFAULT_ID,
            }
        instance = None
        if credential_id and is_uuid(credential_id):
            instance = self.get_queryset().filter(id=credential_id).first()
        if instance:
            return {
                'credential_id': instance.id,
                'asset': instance.asset,
                'username': instance.username,
                'secret_type': instance.secret_type,
            }

        asset = None
        asset_id = self.request.data.get('asset')
        if isinstance(asset_id, dict):
            asset_id = asset_id.get('id') or asset_id.get('pk')
        if (
                asset_id
                and not isinstance(asset_id, (list, tuple))
                and is_uuid(asset_id)
        ):
            asset = Asset.objects.filter(id=asset_id).first()
        username = self.request.data.get('username', '')
        if not isinstance(username, str):
            username = ''
        secret_type = self.request.data.get('secret_type', '')
        if (
                not isinstance(secret_type, str)
                or secret_type not in PERSONAL_CREDENTIAL_SECRET_TYPES
        ):
            secret_type = ''
        return {
            'credential_id': (
                str(credential_id)
                if credential_id and is_uuid(credential_id)
                else None
            ),
            'asset': asset,
            'username': username[:128],
            'secret_type': secret_type,
            'org_id': current_org.id,
        }

    @staticmethod
    def get_failure_reason(exc):
        codes = exc.get_codes() if isinstance(exc, APIException) else 'not_found'
        flattened = []

        def collect(value):
            if isinstance(value, dict):
                for child in value.values():
                    collect(child)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    collect(child)
            elif isinstance(value, str) and value not in flattened:
                flattened.append(value)

        collect(codes)
        return ','.join(flattened[:8])[:240] or 'request_failed'

    def handle_exception(self, exc):
        operation_mapper = {
            'create': 'create',
            'update': 'update',
            'partial_update': 'update',
            'destroy': 'delete',
            'test': 'test',
        }
        operation = operation_mapper.get(getattr(self, 'action', ''))
        if (
                operation
                and isinstance(exc, (APIException, Http404))
                and not isinstance(exc, Throttled)
        ):
            try:
                record_personal_credential_audit(
                    operation=operation,
                    result='failed',
                    failure_reason=self.get_failure_reason(exc),
                    user=self.request.user,
                    **self.get_failure_audit_metadata(),
                )
            except Exception as audit_error:
                logger.warning(
                    'Record personal credential failure audit error: %s',
                    audit_error,
                )
        return super().handle_exception(exc)
