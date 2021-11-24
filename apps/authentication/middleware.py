from django.shortcuts import redirect


class MFAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        white_urls = ['mfa', 'jsi18n', 'static', 'otp']
        for url in white_urls:
            if request.path.find(url) > -1:
                return response
        if request.session.get('auth_mfa_required'):
            return redirect('authentication:login-mfa')
        return response
