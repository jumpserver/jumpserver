from uuid import UUID
from urllib.parse import urlencode

from django.contrib.auth import login
from django.conf import settings
from django.http.response import HttpResponseRedirect
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request

from common.utils.timezone import utcnow
from common.const.http import POST, GET
from common.drf.api import JmsGenericViewSet
from common.drf.serializers import EmptySerializer
from common.permissions import IsSuperUser
from common.utils import reverse
from users.models import User
from ..serializers import SSOTokenSerializer
from ..models import SSOToken
from ..filters import AuthKeyQueryDeclaration
from ..mixins import AuthMixin
from ..errors import SSOAuthClosed


class SSOViewSet(AuthMixin, JmsGenericViewSet):
    queryset = SSOToken.objects.all()
    serializer_classes = {
        'get_login_url': SSOTokenSerializer,
        'login': EmptySerializer
    }

    @action(methods=[POST], detail=False, permission_classes=[IsSuperUser])
    def get_login_url(self, request, *args, **kwargs):
        if not settings.AUTH_SSO:
            raise SSOAuthClosed()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        user = User.objects.get(username=username)

        operator = request.user.username
        # TODO `created_by` 和 `created_by` 可以通过 `ThreadLocal` 统一处理
        token = SSOToken.objects.create(user=user, created_by=operator, updated_by=operator)
        query = {
            'authkey': token.authkey
        }
        login_url = '%s?%s' % (reverse('api-auth:sso-login', external=True), urlencode(query))
        return Response(data={'login_url': login_url})

    @action(methods=[GET], detail=False, filter_backends=[AuthKeyQueryDeclaration], permission_classes=[])
    def login(self, request: Request, *args, **kwargs):
        """
        此接口违反了 `Restful` 的规范
        `GET` 应该是安全的方法，但此接口是不安全的
        """
        authkey = request.query_params.get('authkey')
        try:
            authkey = UUID(authkey)
            token = SSOToken.objects.get(authkey=authkey, expired=False)
            # 先过期，只能访问这一次
            token.expired = True
            token.save()
        except (ValueError, SSOToken.DoesNotExist):
            self.send_auth_signal(success=False, reason=f'authkey invalid: {authkey}')
            return HttpResponseRedirect(reverse('authentication:login'))

        # 判断是否过期
        if (utcnow().timestamp() - token.date_created.timestamp()) > settings.AUTH_SSO_AUTHKEY_TTL:
            self.send_auth_signal(success=False, reason=f'authkey timeout: {authkey}')
            return HttpResponseRedirect(reverse('authentication:login'))

        user = token.user
        login(self.request, user, 'authentication.backends.api.SSOAuthentication')
        self.send_auth_signal(success=True, user=user)
        return HttpResponseRedirect(reverse('index'))
