"""
This module provides decorators to handle redirect URLs during the authentication flow:
1. save_next_to_session: Captures and stores the intended next URL before redirecting to auth provider
2. redirect_to_saved_next_after_auth: Redirects to the stored next URL after successful authentication
"""
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from functools import wraps

from common.utils import get_logger, safe_next_url

logger = get_logger(__file__)


__all__ = ['save_next_to_session', 'redirect_to_saved_next_after_auth']

# Session key for storing the redirect URL after authentication
AUTH_SESSION_NEXT_URL_KEY = 'auth_next_url'


def save_next_to_session(view_func):
    """
    Decorator to capture and store the 'next' parameter from request.GET into session.
    
    This decorator is applied to the authentication request view to preserve the user's
    intended destination URL before redirecting to the authentication provider.
    
    Usage:
        @save_next_to_session
        def get(self, request):
            # Redirect to OAuth2 provider or other auth method
            
    Example flow:
        User accesses: /auth/oauth2/?next=/dashboard/
            ↓ (decorator saves '/dashboard/' to session)
        Redirected to OAuth2 provider for authentication
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        next_url = request.GET.get('next')
        if next_url:
            request.session[AUTH_SESSION_NEXT_URL_KEY] = next_url
            logger.debug(f"[Auth] Saved next_url to session: {next_url}")
        return view_func(self, request, *args, **kwargs)
    return wrapper


def redirect_to_saved_next_after_auth(view_func):
    """
    Decorator to redirect to the previously saved 'next' URL after successful authentication.
    
    This decorator is applied to the authentication callback view. After the user successfully
    authenticates, if a 'next' URL was previously saved in the session, the user will be
    redirected to that URL instead of the default redirect location.
    
    Conditions for redirect:
        - User must be authenticated (request.user.is_authenticated)
        - Session must contain the saved next URL (AUTH_SESSION_NEXT_URL_KEY)
        - The next URL must not be '/' (avoid unnecessary redirects)
        - The next URL must pass security validation (safe_next_url)
    
    If any condition fails, returns the original view response.
    
    Usage:
        @redirect_to_saved_next_after_auth
        def get(self, request):
            # Process authentication callback
            if user_authenticated:
                auth.login(request, user)
                return HttpResponseRedirect(default_url)
            
    Example flow:
        User redirected back from OAuth2 provider: /auth/oauth2/callback/?code=xxx
            ↓ (view processes authentication, user becomes authenticated)
        Decorator checks session for saved next URL
            ↓ (finds '/dashboard/' in session)
        Redirects to: /dashboard/
            ↓ (clears saved URL from session)
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        # Execute the original view method first
        response = view_func(self, request, *args, **kwargs)
        
        # Check if user has been authenticated
        if request.user and request.user.is_authenticated:
            # Check if session contains a saved next URL
            saved_next_url = request.session.get(AUTH_SESSION_NEXT_URL_KEY)
            
            if saved_next_url and saved_next_url != '/':
                # Validate the URL for security
                safe_url = safe_next_url(saved_next_url, request=request)
                if safe_url:
                    # Clear the saved URL from session (one-time use)
                    request.session.pop(AUTH_SESSION_NEXT_URL_KEY, None)
                    logger.debug(f"[Auth] Redirecting authenticated user to saved next_url: {safe_url}")
                    return HttpResponseRedirect(safe_url)
        
        # Return the original response if no redirect conditions are met
        return response
    return wrapper

