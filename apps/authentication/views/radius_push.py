from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from .mfa import _mfa_success_redirect
from .. import errors, mixins
from ..mfa.radius_push import MFARadiusPush

__all__ = ['UserLoginRadiusPushView']


@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserLoginRadiusPushView(mixins.AuthMixin, View):
    http_method_names = ['get', 'post']

    def dispatch(self, request, *args, **kwargs):
        try:
            self.push_user = self.get_user_from_session()
        except errors.SessionEmptyError:
            return JsonResponse({'status': 'session_expired'}, status=401)
        self.push_attempt = MFARadiusPush.login_attempt(request, self.push_user)
        if self.push_attempt is None:
            return JsonResponse({'status': 'unavailable'}, status=403)
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _response(attempt, fallback='unavailable'):
        if not attempt:
            return JsonResponse({'status': fallback})
        status = 'pending' if attempt['status'] == 'queued' else attempt['status']
        data = {'status': status}
        if 'id' in attempt:
            data['attempt'] = attempt['id']
        return JsonResponse(data)

    def get(self, request):
        attempt_id = request.GET.get('attempt')
        return self._response(self.push_attempt.get(attempt_id) if attempt_id else None)

    def post(self, request):
        action = request.POST.get('action')
        attempt_id = request.POST.get('attempt')
        if action == 'cancel' and attempt_id:
            return self._response(self.push_attempt.cancel(attempt_id), 'cancelled')
        if self.request.session.get('auth_mfa') and (
            self.request.session.get('auth_mfa_username') == self.push_user.username
        ):
            return self._complete_response()
        try:
            self.check_mfa_is_block(self.push_user.username, self.get_request_ip())
        except errors.BlockMFAError as exc:
            return JsonResponse({'status': 'blocked', 'message': exc.msg}, status=403)
        if action == 'start':
            return self._start()
        if action == 'complete' and attempt_id:
            attempt = self.push_attempt.transition(attempt_id, {'approved'}, 'consumed')
            if attempt:
                self.mark_mfa_ok(MFARadiusPush.name, self.push_user)
                return self._complete_response()
            return self._response(self.push_attempt.get(attempt_id))
        return JsonResponse({'status': 'unavailable'}, status=400)

    def _start(self):
        outcome = self.push_attempt.enqueue(
            self.push_user, self.get_request_ip(), self.request.session['auth_password_expired_at'],
        )
        return self._response(outcome)

    def _complete_response(self):
        return JsonResponse({'status': 'complete', 'redirect': _mfa_success_redirect(self.request).url})
