from django.dispatch import receiver

from jms_oidc_rp.signals import oidc_user_login_success

from .signals import post_auth_success


@receiver(oidc_user_login_success)
def on_oidc_user_login_success(sender, request, user, **kwargs):
    post_auth_success.send(sender, user=user, request=request)
