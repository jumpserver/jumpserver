from django.conf import settings
from django.core.cache import cache
from oauth2_provider.models import get_application_model

from common.utils import get_logger

logger = get_logger(__name__)

def get_or_create_jumpserver_client_application():
    """Auto get or create OAuth2 JumpServer Client application."""
    Application = get_application_model()
    
    application, created = Application.objects.get_or_create(
        name=settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME,
        defaults={
            'client_type': Application.CLIENT_PUBLIC,
            'authorization_grant_type': Application.GRANT_AUTHORIZATION_CODE,
            'redirect_uris': settings.OAUTH2_PROVIDER_CLIENT_REDIRECT_URI,
            'skip_authorization': True,
        }
    )
    return application


CACHE_OAUTH_SERVER_VIEW_KEY_PREFIX = 'oauth2_provider_metadata'


def clear_oauth2_authorization_server_view_cache():
    logger.info("Clearing OAuth2 Authorization Server Metadata view cache")
    cache_key = f'views.decorators.cache.cache_page.{CACHE_OAUTH_SERVER_VIEW_KEY_PREFIX}.GET*'
    cache.delete_pattern(cache_key)