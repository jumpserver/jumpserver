from django.dispatch import Signal


post_auth_success = Signal(providing_args=('user', 'request'))
post_auth_failed = Signal(providing_args=('username', 'request', 'reason'))


user_auth_success = Signal(providing_args=('user', 'request', 'backend', 'create'))
user_auth_failed = Signal(providing_args=('username', 'request', 'reason', 'backend'))
