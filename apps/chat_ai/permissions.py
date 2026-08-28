from django.conf import settings
from rest_framework.permissions import BasePermission

from orgs.utils import current_org
from rbac.models import RoleBinding


CHAT_AI_USE_PERMISSION = 'chat_ai.use_chatai'


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


class CanUseChatAI(BasePermission):
    message = 'You do not have permission to use Chat AI.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_valid
            and user.has_perm(CHAT_AI_USE_PERMISSION)
        )
