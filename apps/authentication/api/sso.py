from uuid import UUID
from urllib.parse import urlencode

from django.contrib.auth import login
from django.conf import settings
from django.core.cache import cache
from django.http.response import HttpResponseRedirect
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.permissions import AllowAny
from rest_framework.generics import GenericAPIView

from common.utils.timezone import utc_now
from common.const.http import POST, GET
from common.drf.api import JMSGenericViewSet
from common.drf.serializers import EmptySerializer
from common.permissions import IsSuperUser, IsAppUser
from common.utils import reverse
from common.utils import random_string
from users.models import User
from ..serializers import SSOTokenSerializer
from ..models import SSOToken
from ..filters import AuthKeyQueryDeclaration
from ..mixins import AuthMixin
from ..errors import SSOAuthClosed
from ..const import ENTRY_TOKEN_KEY


NEXT_URL = 'next'
AUTH_KEY = 'authkey'


class SSOViewSet(AuthMixin, JMSGenericViewSet):
    queryset = SSOToken.objects.all()
    serializer_classes = {
        'login_url': SSOTokenSerializer,
        'login': EmptySerializer
    }
    permission_classes = (IsSuperUser,)

    @action(methods=[POST], detail=False, permission_classes=[IsSuperUser], url_path='login-url')
    def login_url(self, request, *args, **kwargs):
        if not settings.AUTH_SSO:
            raise SSOAuthClosed()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        user = User.objects.get(username=username)
        next_url = serializer.validated_data.get(NEXT_URL)

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
        login(self.request, user, 'authentication.backends.api.SSOAuthentication')
        self.send_auth_signal(success=True, user=user)
        return HttpResponseRedirect(next_url)


class SSOBannerApi(GenericAPIView):
    permission_classes = (IsAppUser,)

    def get(self, request):
        local_user_response = {'auth_type': User.Source.local, 'sso_url': ''}

        username = request.query_params.get('username')
        if username is None:
            return Response(data=local_user_response)

        user = User.objects.filter(username=username).first()
        if user is None:
            return Response(data=local_user_response)

        if user.source not in [
            User.Source.saml2, User.Source.openid, User.Source.cas
        ]:
            return Response(data=local_user_response)

        ssh_token = random_string(36)
        entry_token_key = '%s_%s' % (ENTRY_TOKEN_KEY, ssh_token)
        cache.set(entry_token_key, {
            'username': username, 'sso_type': user.source, 'userid': user.id
        }, 300)

        sso_url = reverse('authentication:ssh-sso-entry', external=True)
        sso_url += '?ssh_token=%s' % ssh_token
        return Response(data={'sso_type': user.source,  'sso_url': sso_url})
