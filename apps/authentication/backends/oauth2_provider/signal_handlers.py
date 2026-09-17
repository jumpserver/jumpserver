from django.db.models.signals import post_delete
from django.db.utils import OperationalError, ProgrammingError
from django.dispatch import receiver
from django.conf import settings

from oauth2_provider.models import get_application_model

from common.signals import django_ready
from common.utils import get_logger
from .utils import (
    clear_oauth2_authorization_server_view_cache,
    get_or_create_jumpserver_client_application,
)

__all__ = [
    'on_django_ready_refresh_oauth2_provider_client',
    'on_oauth2_provider_application_deleted',
]


Application = get_application_model()
logger = get_logger(__name__)


@receiver(django_ready)
def on_django_ready_refresh_oauth2_provider_client(sender, **kwargs):
    clear_oauth2_authorization_server_view_cache()
    try:
        get_or_create_jumpserver_client_application()
    except (OperationalError, ProgrammingError):
        # The startup command initializes the client again after database migrations.
        logger.warning('OAuth client initialization deferred: database unavailable or not migrated')


@receiver(post_delete, sender=Application)
def on_oauth2_provider_application_deleted(sender, instance, **kwargs):
    if instance.name == settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME:
        clear_oauth2_authorization_server_view_cache()
