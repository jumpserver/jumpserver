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
        return self.check_user_permission(request.user, obj.safe, view.model, view=view)

    @classmethod
    def check_user_permission(cls, user, safe, model, view=None, codename=None):
        assert not (view is None and codename is None), 'view and codename cannot both be None'
        if not codename and view:
            codename = view.extra_action_permission_mapping.get(view.action) or \
                       '{}_{}'.format(convert_action(view.action), model._meta.model_name)
        perm_dict = {
            'safe': str(safe.id),
            'app_label': model._meta.app_label,
            'model_name': model._meta.model_name,
            'codename': codename,
        }
        perm = json.dumps(perm_dict)
        return user.has_perm(perm)
