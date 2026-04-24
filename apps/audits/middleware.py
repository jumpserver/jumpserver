from .signals import write_login_failed_log_if_need



class WriteLoginFailedLogIfNeedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.user.is_authenticated:
            write_login_failed_log_if_need.send(sender=self.__class__, request=request)
        return response
