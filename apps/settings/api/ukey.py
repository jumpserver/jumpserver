from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from authentication.backends.ukey.configuration import get_snapshot
from authentication.backends.ukey.exceptions import UKeyAuthError
from authentication.backends.ukey.providers import get_provider
from rbac.permissions import RBACPermission
from .. import serializers

__all__ = ['UKeyTestingAPI']


class UKeyTestingThrottle(UserRateThrottle):
    rate = '10/min'
    scope = 'ukey_management'


@method_decorator(never_cache, name='dispatch')
class UKeyTestingAPI(GenericAPIView):
    permission_classes = [RBACPermission]
    rbac_perms = {'POST': 'settings.change_auth'}
    serializer_class = serializers.UKeyTestingSerializer
    throttle_classes = [UKeyTestingThrottle]

    def post(self, request):
        # Only provider connection drafts (including its write-only credential).
        # Testing never persists settings or accepts CA private keys.
        snapshot = dict(get_snapshot())
        context = {**self.get_serializer_context(), 'snapshot': snapshot}
        serializer = self.get_serializer(data=request.data, partial=True, context=context)
        serializer.is_valid(raise_exception=True)
        snapshot.update(serializer.validated_data)
        try:
            result = get_provider(snapshot).test_connection()
        except UKeyAuthError as exc:
            raise ValidationError(str(exc)) from None
        return Response(result)
