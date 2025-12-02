from django.conf import settings
from oauth2_provider.models import get_application_model

def get_or_create_jumpserver_client_application():
    """Auto get or create OAuth2 JumpServer Client application."""
    Application = get_application_model()
    
    application, created = Application.objects.get_or_create(
        name='JumpServer Client',
        defaults={
            'client_type': Application.CLIENT_PUBLIC,
            'authorization_grant_type': Application.GRANT_AUTHORIZATION_CODE,
            'redirect_uris': settings.OAUTH2_PROVIDER_CLIENT_REDIRECT_URI,
            'skip_authorization': True,
        }
    )
    return application