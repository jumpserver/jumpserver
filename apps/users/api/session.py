from importlib import import_module

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.api import CommonApiMixin
from orgs.utils import current_org
from users import serializers
from ..models import UserSession


class UserSessionViewSet(CommonApiMixin, viewsets.ModelViewSet):
    http_method_names = ('get', 'post', 'head', 'options', 'trace')
    serializer_class = serializers.UserSessionSerializer
    filterset_fields = ['id', 'ip', 'city', 'type']
    search_fields = ['id', 'ip', 'city']

    rbac_perms = {
        'offline': ['users.offline_usersession']
    }

    @property
    def org_user_ids(self):
        user_ids = current_org.get_members().values_list('id', flat=True)
        return user_ids

    def get_queryset(self):
        queryset = UserSession.objects.filter(date_expired__gt=timezone.now())
        if current_org.is_root():
            return queryset
        user_ids = self.org_user_ids
        queryset = queryset.filter(user_id__in=user_ids)
        return queryset

    @action(['POST'], detail=False, url_path='offline')
    def offline(self, request, *args, **kwargs):
        ids = request.data.get('ids', [])
        queryset = self.get_queryset().exclude(key=request.session.session_key).filter(id__in=ids)
        if not queryset.exists():
            return Response(status=status.HTTP_200_OK)

        keys = queryset.values_list('key', flat=True)
        session_store_cls = import_module(settings.SESSION_ENGINE).SessionStore
        for key in keys:
            session_store_cls(key).delete()
        queryset.delete()
        return Response(status=status.HTTP_200_OK)
