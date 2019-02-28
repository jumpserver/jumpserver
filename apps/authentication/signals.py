from django.dispatch import Signal


post_auth_success = Signal(providing_args=('user', 'request'))
post_auth_failed = Signal(providing_args=('username', 'request', 'reason'))
