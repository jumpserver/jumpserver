"""
API endpoints for theme management
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json


User = get_user_model()

VALID_THEMES = ['auto', 'light', 'dark', 'classic_green']


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_theme_preference(request):
    """
    Get or set user theme preference
    
    GET: Returns current user's theme preference
    POST: Updates user's theme preference
    """
    user = request.user
    
    if request.method == 'GET':
        # Get current theme preference
        theme = getattr(user, 'theme_preference', 'auto')
        return Response({
            'theme': theme,
            'available_themes': [
                {'value': 'auto', 'label': 'Auto (System)'},
                {'value': 'light', 'label': 'Light Theme'},
                {'value': 'dark', 'label': 'Dark Theme'},
                {'value': 'classic_green', 'label': 'Classic Green'},
            ]
        })
    
    elif request.method == 'POST':
        # Update theme preference
        theme = request.data.get('theme')
        
        if not theme:
            return Response(
                {'error': 'Theme parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if theme not in VALID_THEMES:
            return Response(
                {'error': f'Invalid theme. Valid options: {", ".join(VALID_THEMES)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Check if user model has theme_preference field
            if hasattr(user, 'theme_preference'):
                user.theme_preference = theme
                user.save()
                return Response({
                    'message': 'Theme preference updated successfully',
                    'theme': theme
                })
            else:
                return Response(
                    {'error': 'Theme preference not supported. Please run migrations.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': f'Failed to update theme preference: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class ThemeToggleView(View):
    """
    Simple view for theme toggling via AJAX
    """
    
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        try:
            data = json.loads(request.body)
            theme = data.get('theme')
            
            if theme not in VALID_THEMES:
                return JsonResponse({
                    'error': f'Invalid theme. Valid options: {", ".join(VALID_THEMES)}'
                }, status=400)
            
            user = request.user
            if hasattr(user, 'theme_preference'):
                user.theme_preference = theme
                user.save()
                return JsonResponse({
                    'success': True,
                    'theme': theme,
                    'message': 'Theme updated successfully'
                })
            else:
                return JsonResponse({
                    'error': 'Theme preference not supported'
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        user = request.user
        theme = getattr(user, 'theme_preference', 'auto')
        
        return JsonResponse({
            'theme': theme,
            'available_themes': VALID_THEMES
        })


# URL patterns for inclusion in urls.py
from django.urls import path

theme_urlpatterns = [
    path('api/v1/users/theme/', user_theme_preference, name='user-theme-preference'),
    path('api/theme/toggle/', ThemeToggleView.as_view(), name='theme-toggle'),
]
