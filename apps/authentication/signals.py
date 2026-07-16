from django.dispatch import Signal

post_auth_success = Signal()
post_auth_failed = Signal()

backend_auth_failed = Signal()
