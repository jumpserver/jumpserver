from uuid import uuid4

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from common.utils import get_logger
from rbac.permissions import RBACPermission
from users.api.mixins import UserQuerysetMixin
from users.models import User, UKeyCertificateBinding
from users.permissions import UserObjectPermission
from . import challenges
from .binding import binding_version, record_change, verify_identity
from .configuration import REVISION, ensure_enabled, get_revision_snapshot, get_snapshot, locked_snapshot
from .exceptions import UKeyAuthError
from .providers import get_provider
from .sdk import UKeySDKConfig


__all__ = [
    'UKeySDKScriptFileAPIView', 'UKeySDKConfigFileAPIView',
    'UKeyCertEnrollAPIView', 'UKeyCertificateBindingAPI',
]

logger = get_logger(__name__)


@method_decorator(never_cache, name='dispatch')
class UKeySDKScriptFileAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        snapshot = get_snapshot()
        sdk = UKeySDKConfig(snapshot)
        # Builtin clients may use the original URL without version parameters.
        # When supplied, still reject a driver from another configuration.
        versioned = sdk.provider.binding_mode == 'certificate' or any(
            name in request.query_params for name in ('vendor', 'revision')
        )
        if versioned and (request.query_params.get('vendor') != snapshot['AUTH_UKEY_VENDOR']
                          or request.query_params.get('revision') != snapshot[REVISION]):
            return Response({'detail': _('UKey settings have changed. Refresh the page and try again.')}, status=409)
        content = sdk.load_sdk_script_content()
        if content is None:
            raise Http404
        return HttpResponse(content, content_type='application/javascript')


@method_decorator(never_cache, name='dispatch')
class UKeySDKConfigFileAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        if request.query_params.get('revision_only') == '1':
            snapshot = get_revision_snapshot()
            return Response({
                'provider': snapshot['AUTH_UKEY_CA_PROVIDER'],
                'vendor': snapshot['AUTH_UKEY_VENDOR'], 'revision': snapshot[REVISION],
            })
        lang = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME) or settings.LANGUAGE_CODE
        sdk = UKeySDKConfig(get_snapshot())
        admin = request.user.is_authenticated and request.user.has_perm('users.change_user')
        data = sdk.get_sdk_config(lang=lang, include_admin_pin=admin)
        return Response(data)


class UKeyCertEnrollAPIView(APIView):
    rbac_perms = {
        'POST': 'users.change_user',
    }

    def post(self, request):
        snapshot = get_snapshot()
        provider = get_provider(snapshot)
        if not provider.supports_enrollment or not snapshot['AUTH_UKEY_ENROLL_ENABLED']:
            data = {'error': _('Certificate enrollment is not enabled')}
            return Response(data=data, status=400)

        csr_raw = request.data.get('csr')
        if not csr_raw:
            data = {'error': _('CSR is required')}
            return Response(data=data, status=400)

        try:
            signed_cert = provider.enroll(csr_raw)
        except Exception as exc:
            error = _('Certificate signing failed; check the configuration and retry')
            logger.error('UKey certificate signing failed: exception=%s', type(exc).__name__)
            return Response(data={'error': error}, status=400)
        return Response(data={'signed_cert': signed_cert}, status=200)


class UKeyManagementThrottle(UserRateThrottle):
    rate = '10/min'
    scope = 'ukey_management'


class UKeyCertificateBindingSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['challenge', 'bind', 'unbind'])
    revision = serializers.CharField(max_length=32)
    challenge_id = serializers.CharField(max_length=43, required=False)
    cert = serializers.CharField(max_length=21848, required=False, trim_whitespace=False, write_only=True)
    signature = serializers.CharField(max_length=4096, required=False, trim_whitespace=False, write_only=True)
    hardware_serial = serializers.CharField(max_length=128, required=False)
    binding_version = serializers.CharField(max_length=36, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs['action'] == 'bind':
            for key in ('challenge_id', 'cert', 'signature', 'hardware_serial'):
                if not attrs.get(key):
                    raise serializers.ValidationError({key: 'This field is required.'})
        elif attrs['action'] == 'unbind' and 'binding_version' not in attrs:
            raise serializers.ValidationError({'binding_version': 'Reload the binding before unbinding.'})
        return attrs


@method_decorator(never_cache, name='dispatch')
@method_decorator(sensitive_post_parameters(), name='dispatch')
class UKeyCertificateBindingAPI(UserQuerysetMixin, generics.GenericAPIView):
    permission_classes = [RBACPermission, UserObjectPermission]
    rbac_perms = {'GET': 'users.change_user', 'POST': 'users.change_user',
                  'partial_update': 'users.change_user'}
    # Preserve the existing user-management superuser/object restriction.
    action = 'partial_update'
    lookup_url_kwarg = 'user_id'
    serializer_class = UKeyCertificateBindingSerializer
    throttle_classes = [UKeyManagementThrottle]

    def get_throttles(self):
        return [] if self.request.method == 'GET' else super().get_throttles()

    def get(self, request, *args, **kwargs):
        user = self.get_object()
        return Response(self.binding_data(user.pk, get_provider(get_snapshot()).id))

    @staticmethod
    def binding_data(user_id, provider):
        binding = UKeyCertificateBinding.objects.filter(user_id=user_id, provider=provider).first()
        if not binding:
            return {'bound': False, 'binding_version': '', 'hardware_serial': ''}
        return {
            'bound': True, 'binding_version': str(binding.version),
            'hardware_serial': binding.hardware_serial,
            'certificate_fingerprint': binding.certificate_fingerprint,
        }

    def post(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            snapshot = get_snapshot()
            provider = ensure_enabled(snapshot)
            if provider.binding_mode != 'certificate':
                raise UKeyAuthError('Certificate binding is not supported by this CA provider')
            if data['revision'] != snapshot[REVISION]:
                raise UKeyAuthError('UKey configuration changed; refresh and retry')
            action = data['action']
            if action == 'challenge':
                return Response(challenges.issue(request, 'bind', user.pk, binding_version(user.pk, provider.id)))
            if action == 'bind':
                record, snapshot = challenges.consume(request, data['challenge_id'], 'bind', user.pk)
                identity = verify_identity(snapshot, record['code'], data['cert'], data['signature'])
                expected_binding = record['binding_version']
            else:
                expected_binding = data['binding_version']
            with locked_snapshot(snapshot[REVISION]) as current:
                ensure_enabled(current, provider.id)
                # Keep DISTINCT in the scope subquery; lock only the parent user row.
                allowed_users = self.get_queryset().values('pk')
                locked_user = (
                    User.objects.filter(pk__in=allowed_users)
                    .select_for_update()
                    .get(pk=user.pk)
                )
                self.check_object_permissions(request, locked_user)
                if binding_version(user.pk, provider.id) != expected_binding:
                    raise UKeyAuthError('Certificate binding changed; refresh and retry')
                if action == 'bind':
                    UKeyCertificateBinding.objects.update_or_create(user=locked_user, defaults={
                        **identity, 'hardware_serial': data['hardware_serial'], 'version': uuid4(),
                    })
                else:
                    UKeyCertificateBinding.objects.filter(user=locked_user, provider=provider.id).delete()
                transaction.on_commit(lambda: record_change(user, action, provider.id), robust=True)
                result = self.binding_data(user.pk, provider.id)
            return Response(result)
        except IntegrityError:
            raise ValidationError('Certificate is already bound to another user') from None
        except User.DoesNotExist:
            raise ValidationError('Target user is no longer available') from None
        except UKeyAuthError as exc:
            raise ValidationError(str(exc)) from None
