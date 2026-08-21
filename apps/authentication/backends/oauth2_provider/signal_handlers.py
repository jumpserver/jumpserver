from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings

from oauth2_provider.models import get_application_model

from common.signals import django_ready
from .utils import clear_oauth2_authorization_server_view_cache

__all__ = [
    'on_django_ready_clear_oauth2_provider_metadata_cache',
    'on_oauth2_provider_application_deleted',
]


Application = get_application_model()


@receiver(django_ready)
def on_django_ready_clear_oauth2_provider_metadata_cache(sender, **kwargs):
    clear_oauth2_authorization_server_view_cache()


@receiver(post_delete, sender=Application)
def on_oauth2_provider_application_deleted(sender, instance, **kwargs):
    if instance.name == settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME:
        clear_oauth2_authorization_server_view_cache()
