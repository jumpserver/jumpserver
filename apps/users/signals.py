from django.dispatch import Signal


post_user_create = Signal(providing_args=('user',))
post_user_change_password = Signal(providing_args=('user',))
