from django.dispatch import Signal


post_user_create = Signal(providing_args=('user',))
