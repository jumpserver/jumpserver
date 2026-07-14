import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings.ai'

from django.core.asgi import get_asgi_application  # noqa: E402


application = get_asgi_application()
