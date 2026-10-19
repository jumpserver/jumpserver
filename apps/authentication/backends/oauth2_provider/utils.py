from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from oauth2_provider.models import get_application_model

from common.utils import get_logger
from common.utils.lock import DistributedLock

logger = get_logger(__name__)

def get_or_create_jumpserver_client_application():
    """Refresh built-in client callbacks without replacing its credentials."""
    Application = get_application_model()
    name = settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME

    # Name is not unique, and row locks cannot serialize the first insert.
    # Acquire the shared lock before opening the transaction and release after commit.
    with DistributedLock('oauth2-provider-jumpserver-client'), transaction.atomic():
        applications = list(
            Application.objects.select_for_update().filter(name=name).order_by('pk')
        )
        if not applications:
            return Application.objects.create(
                name=name,
                client_type=Application.CLIENT_PUBLIC,
                authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                redirect_uris=settings.OAUTH2_PROVIDER_CLIENT_REDIRECT_URI,
                skip_authorization=True,
            )

        if len(applications) > 1:
            logger.warning(
                'Found %s built-in OAuth clients; using application %s and preserving all credentials and tokens',
                len(applications), applications[0].pk,
            )

        # Older concurrent startups may have created duplicates. Refresh each
        # client's callbacks, preserving its credentials and related tokens.
        for application in applications:
            original_uris = application.redirect_uris.split()
            redirect_uris = [uri for uri in original_uris if not uri.lower().startswith('jms:')]
            missing_uris = [
                uri for uri in settings.OAUTH2_PROVIDER_CLIENT_REDIRECT_URI.split()
                if uri not in redirect_uris
            ]
            if missing_uris or redirect_uris != original_uris:
                application.redirect_uris = ' '.join(redirect_uris + missing_uris)
                application.save(update_fields=['redirect_uris'])
        return applications[0]


CACHE_OAUTH_SERVER_VIEW_KEY_PREFIX = 'oauth2_provider_metadata'


def clear_oauth2_authorization_server_view_cache():
    logger.info("Clearing OAuth2 Authorization Server Metadata view cache")
    cache_key = f'views.decorators.cache.cache_*.{CACHE_OAUTH_SERVER_VIEW_KEY_PREFIX}.*'
    cache.delete_pattern(cache_key)
