from django.http.request import QueryDict
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_out
from django_auth_ldap.backend import populate_user
from .openid import client
from .signals import post_create_openid_user


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if not settings.AUTH_OPENID:
        return

    query = QueryDict('', mutable=True)
    query.update({
        'redirect_uri': settings.BASE_SITE_URL
    })

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


@receiver(populate_user)
def on_ldap_create_user(sender, user, ldap_user, **kwargs):
    if user and user.name != 'admin':
        user.source = user.SOURCE_LDAP
        user.save()
