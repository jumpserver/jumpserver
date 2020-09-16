from django.dispatch import Signal


post_command_executed = Signal(providing_args=('user', 'session_id', 'input', 'asset', 'risk_level'))
