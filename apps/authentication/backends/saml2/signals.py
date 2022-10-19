from django.dispatch import Signal


saml2_create_or_update_user = Signal(providing_args=('user', 'created', 'request', 'attrs'))
