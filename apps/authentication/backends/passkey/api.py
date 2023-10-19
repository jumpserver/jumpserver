from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny

from authentication.mixins import AuthMixin
from common.api import JMSModelViewSet
from .fido import register_begin, register_complete, auth_begin, auth_complete
from .models import Passkey
from .serializer import PasskeySerializer
from ...const import ConfirmType
from ...permissions import UserConfirmation
from ...views import FlashMessageMixin


class PasskeyViewSet(AuthMixin, FlashMessageMixin, JMSModelViewSet):
    serializer_class = PasskeySerializer
    permission_classes = (IsAuthenticated,)

    def get_permissions(self):
        if self.is_swagger_request():
            return super().get_permissions()
        if self.action == 'register':
            self.permission_classes = [
                IsAuthenticated, UserConfirmation.require(ConfirmType.PASSWORD)
            ]
        return super().get_permissions()

    def get_queryset(self):
        return Passkey.objects.filter(user=self.request.user)

    @action(methods=['get', 'post'], detail=False, url_path='register')
    def register(self, request):
        if request.user.source != 'local':
            return JsonResponse({'error': _('Only register passkey for local user')}, status=400)
        if request.method == 'GET':
            register_data, state = register_begin(request)
            return JsonResponse(dict(register_data))
        else:
            passkey = register_complete(request)
            return JsonResponse({'id': passkey.id.__str__(), 'name': passkey.name})

    @action(methods=['get'], detail=False, url_path='login', permission_classes=[AllowAny])
    def login(self, request):
        return render(request, 'authentication/passkey.html', {})

    def redirect_to_error(self, error):
        self.send_auth_signal(success=False, username='unknown', reason='passkey')
        return render(self.request, 'authentication/passkey.html', {'error': error})

    @action(methods=['get', 'post'], detail=False, url_path='auth', permission_classes=[AllowAny])
    def auth(self, request):
        if request.method == 'GET':
            auth_data = auth_begin(request)
            return JsonResponse(dict(auth_data))

        try:
            user = auth_complete(request)
        except ValueError as e:
            return self.redirect_to_error(str(e))

        if not user:
            return self.redirect_to_error(_('Auth failed'))

        try:
            self.check_oauth2_auth(user, settings.AUTH_BACKEND_PASSKEY)
            return self.redirect_to_guard_view()
        except Exception as e:
            msg = getattr(e, 'msg', '') or str(e)
            return self.redirect_to_error(msg)
