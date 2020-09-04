from common.utils.redis import RedisClient
from django.conf import settings
from django.contrib.auth import user_logged_in
from django.core.cache import cache
from django.dispatch import receiver

from jms_oidc_rp.signals import openid_user_login_failed, openid_user_login_success
from jumpserver.const import CONFIG

from .signals import post_auth_success, post_auth_failed


@receiver(openid_user_login_success)
def on_oidc_user_login_success(sender, request, user, **kwargs):
    post_auth_success.send(sender, user=user, request=request)


@receiver(openid_user_login_failed)
def on_oidc_user_login_failed(sender, username, request, reason, **kwargs):
    post_auth_failed.send(sender, username=username, request=request, reason=reason)


@receiver(user_logged_in)
def on_user_auth_access(sender, user, request, **kwargs):
    # 仅允许单机登录
    user_id = str(user.id)
    session_key = cache.get(user_id)
    if session_key and session_key != request.session.session_key:
        redis_client = RedisClient(host=CONFIG.REDIS_HOST, port=CONFIG.REDIS_PORT,
                                   password=CONFIG.REDIS_PASSWORD, db=CONFIG.REDIS_DB_SESSION)
        redis_client.delete(settings.SESSION_REDIS['prefix'] + ':' + session_key)
    cache.set(user_id, request.session.session_key)
