from django.dispatch import Signal


oauth2_create_or_update_user = Signal(
    providing_args=['request', 'user', 'created', 'name', 'username', 'email']
)
oauth2_user_login_success = Signal(providing_args=['request', 'user'])
oauth2_user_login_failed = Signal(providing_args=['request', 'username', 'reason'])

