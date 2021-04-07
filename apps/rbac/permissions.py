import json
from django.utils.translation import ugettext_lazy as _
from rest_framework.permissions import IsAuthenticated, BasePermission
from .utils import convert_action


class IsNotBuiltIn(BasePermission):
    message = _('Cannot update/delete built-in objects')

    def has_object_permission(self, request, view, obj):
        return not obj.is_builtin


class SafeRolePermission(IsAuthenticated, BasePermission):

    def has_object_permission(self, request, view, obj):
        has_permission = self.check_user_permission(
            user=request.user, safe=obj.safe, model=view.model, view_action=view.action
        )
        return has_permission

    @classmethod
    def check_user_permission(cls, user, safe, model, view_action):
        perm_dict = {
            'safe': str(safe.id), 'app_label': model._meta.app_label,
            'action': convert_action(view_action), 'model_name': model._meta.model_name,
        }
        perm = json.dumps(perm_dict)
        return user.has_perm(perm)
