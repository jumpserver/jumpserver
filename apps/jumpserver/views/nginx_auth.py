from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

__all__ = ['internal_auth']


# nginx auth_request
# If the returns a 2xx response code, the access is allowed.
# If it returns 401 or 403, the access is denied with the corresponding error code.

@csrf_exempt
def internal_auth(request):
    if not request.user.is_authenticated:
        return HttpResponse("Forbidden", status=401, )
    x_original_uri = request.headers.get('X-Original-Uri')
    if not request.user.is_superuser or not x_original_uri:
        return HttpResponse(f"Forbidden {x_original_uri}", status=401, )
    return HttpResponse("OK")
