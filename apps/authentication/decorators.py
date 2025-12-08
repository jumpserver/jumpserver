"""
This module provides decorators to handle redirect URLs during the authentication flow:
1. pre_save_next_to_session: Captures and stores the intended next URL before redirecting to auth provider
2. redirect_to_pre_save_next_after_auth: Redirects to the stored next URL after successful authentication
3. post_save_next_to_session: Copies the stored next URL to session['next'] after view execution
"""
from urllib.parse import urlparse

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from functools import wraps

from common.utils import get_logger, safe_next_url
from .const import USER_LOGIN_GUARD_VIEW_REDIRECT_FIELD

logger = get_logger(__file__)


__all__ = [
    'pre_save_next_to_session', 'redirect_to_pre_save_next_after_auth', 
    'post_save_next_to_session_if_guard_redirect'
]

# Session key for storing the redirect URL after authentication
AUTH_SESSION_NEXT_URL_KEY = 'auth_next_url'


def pre_save_next_to_session(get_next_url=None):
    """
    Decorator to capture and store the 'next' parameter into session BEFORE view execution.
    
    This decorator is applied to the authentication request view to preserve the user's
    intended destination URL before redirecting to the authentication provider.
    
    Args:
        get_next_url: Optional callable that extracts the next URL from request.
                      Default: lambda req: req.GET.get('next')
                      
    Usage:
        # Use default (request.GET.get('next'))
        @pre_save_next_to_session()
        def get(self, request):
            pass
        
        # Custom extraction from POST data
        @pre_save_next_to_session(get_next_url=lambda req: req.POST.get('next'))
        def post(self, request):
            pass
        
        # Custom extraction from both GET and POST
        @pre_save_next_to_session(
            get_next_url=lambda req: req.GET.get('next') or req.POST.get('next')
        )
        def get(self, request):
            pass
            
    Example flow:
        User accesses: /auth/oauth2/?next=/dashboard/
            ↓ (decorator saves '/dashboard/' to session)
        Redirected to OAuth2 provider for authentication
    """
    # Default function to extract next URL from request.GET
    if get_next_url is None:
        get_next_url = lambda req: req.GET.get('next')
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            next_url = get_next_url(request)
            if next_url:
                request.session[AUTH_SESSION_NEXT_URL_KEY] = next_url
                logger.debug(f"[Auth] Saved next_url to session: {next_url}")
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def redirect_to_pre_save_next_after_auth(view_func):
    """
    Decorator to redirect to the previously saved 'next' URL after successful authentication.
    
    This decorator is applied to the authentication callback view. After the user successfully
    authenticates, if a 'next' URL was previously saved in the session (by pre_save_next_to_session),
    the user will be redirected to that URL instead of the default redirect location.
    
    Conditions for redirect:
        - User must be authenticated (request.user.is_authenticated)
        - Session must contain the saved next URL (AUTH_SESSION_NEXT_URL_KEY)
        - The next URL must not be '/' (avoid unnecessary redirects)
        - The next URL must pass security validation (safe_next_url)
    
    If any condition fails, returns the original view response.
    
    Usage:
        @redirect_to_pre_save_next_after_auth
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


def post_save_next_to_session_if_guard_redirect(view_func):
    """
    Decorator to copy AUTH_SESSION_NEXT_URL_KEY to session['next'] after view execution, 
    but only if redirecting to login-guard view.
    
    This decorator is applied AFTER view execution. It copies the value from 
    AUTH_SESSION_NEXT_URL_KEY (internal storage) to 'next' (standard session key) 
    for use by downstream code.
    
    Only sets the 'next' session key when the response is a redirect to guard-view
    (i.e., response with redirect status code and location path matching login-guard view URL).
    
    Usage:
        @post_save_next_to_session_if_guard_redirect
        def get(self, request):
            # Process the request and return response
            if some_condition:
                return self.redirect_to_guard_view()  # Decorator will copy next to session
            return HttpResponseRedirect(url)  # Decorator won't copy if not to guard-view
    
    Example flow:
        View executes and returns redirect to guard view
            ↓ (response is redirect with 'login-guard' in Location)
        Decorator checks if response is redirect to guard-view and session has saved next URL
            ↓ (copies AUTH_SESSION_NEXT_URL_KEY to session['next'])
        User is redirected to guard-view with 'next' available in session
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        # Execute the original view method
        response = view_func(self, request, *args, **kwargs)
        
        # Check if response is a redirect to guard view
        # Redirect responses typically have status codes 301, 302, 303, 307, 308
        is_guard_redirect = False
        if hasattr(response, 'status_code') and response.status_code in (301, 302, 303, 307, 308):
            # Check if the redirect location is to guard view
            location = response.get('Location', '')
            if location:
                # Extract path from location URL (handle both absolute and relative URLs)
                parsed_url = urlparse(location)
                path = parsed_url.path
                
                # Check if path matches guard view URL pattern
                guard_view_url = reverse('authentication:login-guard')
                if path == guard_view_url:
                    is_guard_redirect = True
        
        # Only set 'next' if response is a redirect to guard view
        if is_guard_redirect:
            # Copy AUTH_SESSION_NEXT_URL_KEY to 'next' if it exists
            saved_next_url = request.session.get(AUTH_SESSION_NEXT_URL_KEY)
            if saved_next_url:
                # 这里 'next' 是 UserLoginGuardView.redirect_field_name
                request.session[USER_LOGIN_GUARD_VIEW_REDIRECT_FIELD] = saved_next_url
                logger.debug(f"[Auth] Copied {AUTH_SESSION_NEXT_URL_KEY} to 'next' in session: {saved_next_url}")
        
        return response
    return wrapper
