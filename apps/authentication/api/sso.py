from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.contrib.auth import login
from django.http.response import HttpResponseRedirect
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from common.api import JMSGenericViewSet
from common.const.http import POST, GET
from common.permissions import OnlySuperUser
from common.serializers import EmptySerializer
from common.utils import reverse, safe_next_url
from common.utils.timezone import utc_now
from users.models import User
from ..errors import SSOAuthClosed
from ..filters import AuthKeyQueryDeclaration
from ..mixins import AuthMixin
from ..models import SSOToken
from ..serializers import SSOTokenSerializer

NEXT_URL = 'next'
AUTH_KEY = 'authkey'


class SSOViewSet(AuthMixin, JMSGenericViewSet):
    queryset = SSOToken.objects.all()
    serializer_classes = {
        'login_url': SSOTokenSerializer,
        'login': EmptySerializer
    }

    @action(methods=[POST], detail=False, permission_classes=[OnlySuperUser], url_path='login-url')
    def login_url(self, request, *args, **kwargs):
        if not settings.AUTH_SSO:
            raise SSOAuthClosed()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        user = User.objects.get(username=username)
        next_url = serializer.validated_data.get(NEXT_URL)
        next_url = safe_next_url(next_url, request=request)

        operator = request.user.username
        # TODO `created_by` 和 `created_by` 可以通过 `ThreadLocal` 统一处理
        token = SSOToken.objects.create(user=user, created_by=operator, updated_by=operator)
        query = {
            AUTH_KEY: token.authkey,
            NEXT_URL: next_url or ''
        }
        login_url = '%s?%s' % (reverse('api-auth:sso-login', external=True), urlencode(query))
        return Response(data={'login_url': login_url})

    @action(methods=[GET], detail=False, filter_backends=[AuthKeyQueryDeclaration], permission_classes=[AllowAny])
    def login(self, request: Request, *args, **kwargs):
        """
        此接口违反了 `Restful` 的规范
        `GET` 应该是安全的方法，但此接口是不安全的
        """
        request.META['HTTP_X_JMS_LOGIN_TYPE'] = 'W'
        authkey = request.query_params.get(AUTH_KEY)
        next_url = request.query_params.get(NEXT_URL)
        if not next_url or not next_url.startswith('/'):
            next_url = reverse('index')

        if not authkey:
            raise serializers.ValidationError("authkey is required")

        try:
            authkey = UUID(authkey)
            token = SSOToken.objects.get(authkey=authkey, expired=False)
            # 先过期，只能访问这一次
            token.expired = True
            token.save()
        except (ValueError, SSOToken.DoesNotExist):
            self.send_auth_signal(success=False, reason='authkey_invalid')
            return HttpResponseRedirect(next_url)

        # 判断是否过期
        if (utc_now().timestamp() - token.date_created.timestamp()) > settings.AUTH_SSO_AUTHKEY_TTL:
            self.send_auth_signal(success=False, reason='authkey_timeout')
            return HttpResponseRedirect(next_url)

        user = token.user
        login(self.request, user, settings.AUTH_BACKEND_SSO)
        self.send_auth_signal(success=True, user=user)
        return HttpResponseRedirect(next_url)
