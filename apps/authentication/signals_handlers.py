from django.http.request import QueryDict
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_out
from django_auth_ldap.backend import populate_user

from users.models import User
from .backends.openid import new_client
from .backends.openid.signals import (
    post_create_or_update_openid_user, post_openid_login_success
)
from .signals import post_auth_success


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if not settings.AUTH_OPENID:
        return
    if not settings.AUTH_OPENID_SHARE_SESSION:
        return
    query = QueryDict('', mutable=True)
    query.update({
        'redirect_uri': settings.BASE_SITE_URL
    })
    client = new_client()
    openid_logout_url = "%s?%s" % (
        client.get_url_end_session_endpoint(),
        query.urlencode()
    )
    request.COOKIES['next'] = openid_logout_url


@receiver(post_create_or_update_openid_user)
def on_post_create_or_update_openid_user(sender, user=None,  created=True, **kwargs):
    if created and user and user.username != 'admin':
        user.source = user.SOURCE_OPENID
        user.save()


@receiver(post_openid_login_success)
def on_openid_login_success(sender, user=None, request=None, **kwargs):
    post_auth_success.send(sender=sender, user=user, request=request)


@receiver(populate_user)
def on_ldap_create_user(sender, user, ldap_user, **kwargs):
    if user and user.username not in ['admin']:
        exists = User.objects.filter(username=user.username).exists()
        if not exists:
            user.source = user.SOURCE_LDAP
            user.save()



