from django.dispatch import Signal


saml2_create_or_update_user = Signal(providing_args=('user', 'created', 'request', 'attrs'))
saml2_user_authenticated = Signal(providing_args=('user', 'created', 'request'))
saml2_user_authentication_failed = Signal(providing_args=('request', 'username', 'reason'))
