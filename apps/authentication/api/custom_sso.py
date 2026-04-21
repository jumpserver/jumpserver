from django.utils.module_loading import import_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.http.response import HttpResponseRedirect

from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from rbac.models import SystemRole, SystemRoleBinding
from common.utils import get_logger
from ..mixins import AuthMixin

__all__  = ['CustomSSOLoginAPIView']

logger = get_logger(__file__)


custom_sso_authenticate_method = None

if settings.AUTH_CUSTOM_SSO:
    ''' 保证自定义 SSO 认证方法在服务运行时不能被更改，只在第一次调用时加载一次 '''
    try:
        custom_auth_method_path = 'data.auth.custom_sso.authenticate'
        custom_sso_authenticate_method = import_string(custom_auth_method_path)
    except Exception as e:
        logger.warning('Import custom SSO auth method failed: {}, Maybe not enabled'.format(e))


class CustomSSOLoginAPIView(AuthMixin, RetrieveAPIView):

    permission_classes = [AllowAny]

    next_url = '/'

    def is_enabled(self):
        return settings.AUTH_CUSTOM_SSO and callable(custom_sso_authenticate_method)

    def retrieve(self, request, *args, **kwargs):
        if not self.is_enabled():
            error = 'Custom SSO authentication is disabled.'
            return Response({'detail': error}, status=status.HTTP_403_FORBIDDEN)

        query_params = {}
        for param in settings.AUTH_CUSTOM_SSO_QUERY_PARAMS:
            value = self.request.query_params.get(param)
            if not value:
                error = f'Missing required query parameter: {param}'
                return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
            query_params[param] = value
        
        user, error = self.authenticate(**query_params)
        if user:
            login(request, user, backend=settings.AUTH_BACKEND_CUSTOM_SSO)
            self.send_auth_signal(success=True, user=user)
            return HttpResponseRedirect(self.next_url)
        else:
            self.send_auth_signal(success=False, reason=error)
            return Response({'detail': error}, status=status.HTTP_401_UNAUTHORIZED)

    def authenticate(self, **query_params):
        try:
            userinfo, error = custom_sso_authenticate_method(**query_params)
            if error:
                return None, error
            self.next_url = userinfo.get('next_url', '/')
        except Exception as e:
            error = f'Custom SSO authenticate error: {e}'
            return None, error
        
        try:
            user = self.get_or_create_user_from_userinfo(userinfo)
            return user, ''
        except Exception as e:
            error = f'Custom SSO get or create user error: {e}'
            return None, error

    def get_or_create_user_from_userinfo(self, userinfo: dict):
        User = get_user_model()
        username = userinfo.get('username')
        if username == 'admin':
            user = User.objects.filter(username='admin').first()
            return user
        
        name = userinfo.get('name')
        email = userinfo.get('email')
        defaults = {'name': name, 'email': email}
        user, created = get_user_model().objects.get_or_create(
            username=username, defaults=defaults
        )
        if created:
            system_role_name = userinfo.get('system_role_name')
            system_role = SystemRole.objects.filter(name=system_role_name).first()
            sys_role_binding = SystemRoleBinding(user=user, role=system_role)
            sys_role_binding.save()
        
        return user
