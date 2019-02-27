from django.dispatch import Signal


post_create_openid_user = Signal(providing_args=('user',))
post_auth_success = Signal(providing_args=('user', 'request'))
post_auth_failed = Signal(providing_args=('username', 'request', 'reason'))
