from django.dispatch import Signal

post_auth_success = Signal()
post_auth_failed = Signal()

user_auth_success = Signal()
user_auth_failed = Signal()
