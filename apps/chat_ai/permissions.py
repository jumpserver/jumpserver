from django.conf import settings
from rest_framework.permissions import BasePermission

from orgs.utils import current_org
from rbac.models import RoleBinding


class ChatAIServicePermission(BasePermission):
    message = 'Chat AI APIs are only available from the independent AI service.'

    def has_permission(self, request, view):
        return settings.ROOT_URLCONF == 'jumpserver.ai_urls'


class ChatAIOrgPermission(BasePermission):
    message = 'You do not have access to the selected organization.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_valid:
            return False
        if user.is_superuser:
            return True
        if current_org.is_root():
            return RoleBinding.objects.filter(user=user, org=None).exists()
        return RoleBinding.objects.filter(user=user, org_id=current_org.id).exists()
