from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import reverse
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet

from authentication.mixins import AuthMixin
from .fido import register_begin, register_complete, auth_begin
from .models import UserPasskey
from .serializer import PassKeySerializer
from ...views import FlashMessageMixin


class PassKeyViewSet(AuthMixin, FlashMessageMixin, ModelViewSet):
    serializer_class = PassKeySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return UserPasskey.objects.filter(user=self.request.user)

    @action(methods=['get'], detail=False)
    def register_begin(self, request):
        register_data, state = register_begin(request)
        return JsonResponse(dict(register_data))

    @action(methods=['post'], detail=False)
    def register_complete(self, request):
        passkey = register_complete(request)
        return JsonResponse({'id': passkey.id.__str__(), 'name': passkey.name})

    @action(methods=['get'], detail=False, url_path='auth', permission_classes=[AllowAny])
    def auth(self, request):
        return render(request, 'authentication/passkey.html', {})

    @action(methods=['get'], detail=False, url_path='auth-begin', permission_classes=[AllowAny])
    def auth_begin(self, request):
        auth_data = auth_begin(request)
        return JsonResponse(dict(auth_data))

    def redirect_to_error(self, msg):
        login_url = reverse('authentication:login')
        self.set_login_failed_mark()
        response = self.get_failed_response(login_url, title=msg, msg=msg)
        return response

    @action(methods=['post'], detail=False, url_path='auth-complete', permission_classes=[AllowAny])
    def auth_complete(self, request):
        from .fido import auth_complete
        user = auth_complete(request)

        if not user:
            return self.redirect_to_error('认证失败')

        try:
            self.check_oauth2_auth(user, settings.AUTH_BACKEND_PASSKEY)
            return self.redirect_to_guard_view()
        except Exception as e:
            msg = getattr(e, 'msg', '') or str(e)
            return self.redirect_to_error(msg)
