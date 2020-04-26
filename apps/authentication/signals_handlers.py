from django.dispatch import receiver

from jms_oidc_rp.signals import oidc_user_login_success, oidc_user_login_failed

from .signals import post_auth_success, post_auth_failed


@receiver(oidc_user_login_success)
def on_oidc_user_login_success(sender, request, user, **kwargs):
    post_auth_success.send(sender, user=user, request=request)


@receiver(oidc_user_login_failed)
def on_oidc_user_login_failed(sender, username, request, reason, **kwargs):
    post_auth_failed.send(sender, username=username, request=request, reason=reason)
