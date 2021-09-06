from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from common.permissions import IsAppUser, IsSuperUser
from common.const.http import PATCH
from orgs.mixins.api import OrgModelViewSet
from .. import serializers, models

__all__ = ['SessionSharingViewSet', 'SessionJoinRecordsViewSet']


class SessionSharingViewSet(OrgModelViewSet):
    serializer_class = serializers.SessionSharingSerializer
    permission_classes = (IsAppUser | IsSuperUser, )
    search_fields = ('session', 'creator', 'is_active', 'expired_time')
    filterset_fields = search_fields
    model = models.SessionSharing

    def create(self, request, *args, **kwargs):
        if not settings.SECURITY_SESSION_SHARE:
            detail = _('Secure session sharing settings is disabled')
            raise MethodNotAllowed(self.action, detail=detail)
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)


class SessionJoinRecordsViewSet(OrgModelViewSet):
    serializer_class = serializers.SessionJoinRecordSerializer
    permission_classes = (IsAppUser | IsSuperUser, )
    search_fields = (
        'sharing', 'session', 'joiner', 'date_joined', 'date_left',
        'login_from', 'is_success', 'is_finished'
    )
    filterset_fields = search_fields
    model = models.SessionJoinRecord

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
        except ValidationError as e:
            error = e.args[0] if e.args else ''
            response = Response(
                data={'error': str(error)}, status=e.status_code
            )
        return response

    def perform_create(self, serializer):
        instance = serializer.save()
        self.can_join(instance)

    @staticmethod
    def can_join(instance):
        can_join, reason = instance.can_join()
        if not can_join:
            instance.join_failed(reason=reason)
            raise ValidationError(reason)

    @action(methods=[PATCH], detail=True)
    def finished(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.finished()
        return Response(data={'msg': 'ok'})

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)
