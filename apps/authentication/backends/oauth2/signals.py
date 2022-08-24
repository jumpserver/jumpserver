from django.dispatch import Signal


oauth2_create_or_update_user = Signal(
    providing_args=['request', 'user', 'created', 'name', 'username', 'email']
)

