import time

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

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
        confirm_mfa = request.GET.get('mfa')
        request.session.pop('passkey_confirm_mfa', None)
        request.session.pop('fido2_state', None)
        if confirm_mfa:
            if not request.user.is_authenticated or settings.SAFE_MODE:
                raise PermissionDenied(_('Auth failed'))
            request.session['passkey_confirm_mfa'] = str(request.user.pk)
        return render(request, 'authentication/passkey.html', {})

    def redirect_to_error(self, error):
        self.send_auth_signal(success=False, username='unknown', reason='passkey')
        return render(self.request, 'authentication/passkey.html', {'error': error})

    @action(methods=['get', 'post'], detail=False, url_path='auth', permission_classes=[AllowAny])
    def auth(self, request):
        confirm_user_id = request.session.get('passkey_confirm_mfa')
        if confirm_user_id and (
            not request.user.is_authenticated or settings.SAFE_MODE
            or confirm_user_id != str(request.user.pk)
        ):
            request.session.pop('passkey_confirm_mfa', None)
            request.session.pop('fido2_state', None)
            raise PermissionDenied(_('Auth failed'))

        if request.method == 'GET':
            auth_data = auth_begin(request)
            return JsonResponse(dict(auth_data))

        try:
            user = auth_complete(request)
        except ValueError as e:
            return self.redirect_to_error(str(e))

        if not user:
            return self.redirect_to_error(_('Auth failed'))

        if confirm_user_id:
            if user.pk != request.user.pk:
                return self.redirect_to_error(_('Auth failed'))
            request.session['CONFIRM_LEVEL'] = ConfirmType.values.index('mfa') + 1
            request.session['CONFIRM_TIME'] = int(time.time())
            request.session['CONFIRM_TYPE'] = ConfirmType.MFA
            request.session['CONFIRM_USER_ID'] = str(request.user.pk)
            request.session.pop('passkey_confirm_mfa', None)
            return Response('ok')

        try:
            self.check_oauth2_auth(user, settings.AUTH_BACKEND_PASSKEY)
            # 如果开启了安全模式，passkey 不能作为 MFA
            if not settings.SAFE_MODE:
                self.mark_mfa_ok('passkey', user)
            return self.redirect_to_guard_view()
        except Exception as e:
            msg = getattr(e, 'msg', '') or str(e)
            return self.redirect_to_error(msg)
