from django.http.request import QueryDict
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_out
from django.utils import timezone
from django_auth_ldap.backend import populate_user

from common.utils import get_request_ip
from .backends.openid import new_client
from .backends.openid.signals import (
    post_create_openid_user, post_openid_login_success
)
from .tasks import write_login_log_async
from .signals import post_auth_success, post_auth_failed


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if not settings.AUTH_OPENID:
        return

    query = QueryDict('', mutable=True)
    query.update({
        'redirect_uri': settings.BASE_SITE_URL
    })

    client = new_client()
    openid_logout_url = "%s?%s" % (
        client.openid_connect_client.get_url(
            name='end_session_endpoint'),
        query.urlencode()
    )

    request.COOKIES['next'] = openid_logout_url


@receiver(post_create_openid_user)
def on_post_create_openid_user(sender, user=None,  **kwargs):
    if user and user.username != 'admin':
        user.source = user.SOURCE_OPENID
        user.save()


@receiver(post_openid_login_success)
def on_openid_login_success(sender, user=None, request=None, **kwargs):
    post_auth_success.send(sender=sender, user=user, request=request)


@receiver(populate_user)
def on_ldap_create_user(sender, user, ldap_user, **kwargs):
    if user and user.name != 'admin':
        user.source = user.SOURCE_LDAP
        user.save()


def generate_data(username, request):
    if not request.user.is_anonymous and request.user.is_app:
        login_ip = request.data.get('remote_addr', None)
        login_type = request.data.get('login_type', '')
        user_agent = request.data.get('HTTP_USER_AGENT', '')
    else:
        login_ip = get_request_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        login_type = 'W'
    data = {
        'username': username,
        'ip': login_ip,
        'type': login_type,
        'user_agent': user_agent,
        'datetime': timezone.now()
    }
    return data


@receiver(post_auth_success)
def on_user_auth_success(sender, user, request, **kwargs):
    data = generate_data(user.username, request)
    data.update({'mfa': int(user.otp_enabled), 'status': True})
    write_login_log_async.delay(**data)


@receiver(post_auth_failed)
def on_user_auth_failed(sender, username, request, reason, **kwargs):
    data = generate_data(username, request)
    data.update({'reason': reason, 'status': False})
    write_login_log_async.delay(**data)
