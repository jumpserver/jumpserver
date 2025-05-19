from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.contrib.auth import login
from django.http.response import HttpResponseRedirect
from rest_framework import serializers
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from authentication.errors import ACLError
from common.api import JMSGenericViewSet
from common.const.http import POST, GET
from common.permissions import OnlySuperUser
from common.serializers import EmptySerializer
from common.utils import reverse, safe_next_url
from common.utils.timezone import utc_now
from users.models import User
from users.utils import LoginBlockUtil, LoginIpBlockUtil
from ..errors import (
    SSOAuthClosed, AuthFailedError, LoginConfirmBaseError, SSOAuthKeyTTLError
)
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
        status_code = status.HTTP_400_BAD_REQUEST
        request.META['HTTP_X_JMS_LOGIN_TYPE'] = 'W'
        authkey = request.query_params.get(AUTH_KEY)
        next_url = request.query_params.get(NEXT_URL)
        if not next_url or not next_url.startswith('/'):
            next_url = reverse('index')

        try:
            if not authkey:
                raise serializers.ValidationError("authkey is required")

            authkey = UUID(authkey)
            token = SSOToken.objects.get(authkey=authkey, expired=False)
        except (ValueError, SSOToken.DoesNotExist, serializers.ValidationError) as e:
            error_msg = str(e)
            self.send_auth_signal(success=False, reason=error_msg)
            return Response({'error': error_msg}, status=status_code)

        error_msg = None
        user = token.user
        username = user.username
        ip = self.get_request_ip()

        try:
            if (utc_now().timestamp() - token.date_created.timestamp()) > settings.AUTH_SSO_AUTHKEY_TTL:
                raise SSOAuthKeyTTLError()

            self._check_is_block(username, True)
            self._check_only_allow_exists_user_auth(username)
            self._check_login_acl(user, ip)
            self.check_user_login_confirm_if_need(user)

            self.request.session['auth_backend'] = settings.AUTH_BACKEND_SSO
            login(self.request, user, settings.AUTH_BACKEND_SSO)
            self.send_auth_signal(success=True, user=user)

            LoginIpBlockUtil(ip).clean_block_if_need()
            LoginBlockUtil(username, ip).clean_failed_count()
        except (ACLError, LoginConfirmBaseError):  # 无需记录日志
            pass
        except (AuthFailedError, SSOAuthKeyTTLError) as e:
            error_msg = e.msg
        except Exception as e:
            error_msg = str(e)
        finally:
            token.expired = True
            token.save()

        if error_msg:
            self.send_auth_signal(success=False, username=username, reason=error_msg)
            return Response({'error': error_msg}, status=status_code)
        else:
            return HttpResponseRedirect(next_url)
