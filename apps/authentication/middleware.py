from django.shortcuts import redirect


class MFAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.find('/auth/login/otp/') > -1:
            return response
        if request.session.get('auth_mfa_required'):
            return redirect('authentication:login-otp')
        return response
