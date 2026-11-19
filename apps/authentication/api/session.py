from django.db import transaction
from django.utils.decorators import method_decorator
from django.utils.crypto import constant_time_compare
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.api.web_session_lock import WebSessionControlAuthentication
from authentication.services.idle_lock import idle_lock_limits, personal_idle_lock_time, effective_idle_lock_time
from authentication.services.web_session_lock import session_scope
from common.permissions import IsValidUser

__all__ = ['UserSessionApi']


class PageCloseSerializer(serializers.Serializer):
    scope = serializers.RegexField(r'^[a-f0-9]{40}$', required=False)
    page_id = serializers.RegexField(r'^[a-zA-Z0-9-]{1,128}$')


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class UserSessionApi(APIView):
    authentication_classes = (WebSessionControlAuthentication,)
    permission_classes = (IsValidUser,)
    http_method_names = ('post', 'options')

    def post(self, request):
        serializer = PageCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if 'scope' in data and not constant_time_compare(data['scope'], session_scope(request.session.session_key)):
            return Response({'code': 'web_session_changed'}, status=409)
        idle_time = effective_idle_lock_time(
            idle_lock_limits(use_cache=True)['web_idle_lock_time'],
            personal_idle_lock_time(request.user.pk, 'web_idle_lock_time'),
        )
        request.session.update_page(data['page_id'], entering=False, lock_on_close=idle_time > 0)
        return Response({'ok': True})
