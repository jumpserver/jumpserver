from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.conf import settings

from oauth2_provider.models import get_application_model

from .utils import clear_oauth2_authorization_server_view_cache

Application = get_application_model()

__all__ = ['on_oauth2_provider_application_deleted']

@receiver(post_delete, sender=Application)
def on_oauth2_provider_application_deleted(sender, instance, **kwargs):
    if instance.name == settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME:
        clear_oauth2_authorization_server_view_cache()

