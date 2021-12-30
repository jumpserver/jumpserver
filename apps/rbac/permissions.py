from rest_framework import permissions, exceptions
from django.utils.datastructures import OrderedSet


class RBACPermission(permissions.DjangoModelPermissions):
    default_action_perms_map = {
        'list': ['%(app_label)s.view_%(model_name)s'],
        'retrieve': ['%(app_label)s.view_%(model_name)s'],
        'create': ['%(app_label)s.add_%(model_name)s'],
        'update': ['%(app_label)s.change_%(model_name)s'],
        'partial_update': ['%(app_label)s.change_%(model_name)s'],
        'delete': ['%(app_label)s.delete_%(model_name)s'],
    }

    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    def get_method_perms_map(self):
        return self.perms_map

    def get_action_perms_map(self, view):
        if hasattr(view, 'get_action_perms_map'):
            return view.get_action_perms_map()

        perms = {k: v for k, v in self.default_action_perms_map.items()}
        if hasattr(view, 'action_perms_map'):
            for k, v in view.action_perms_map.items():
                perms[k] = v
        return perms

    @classmethod
    def get_action_default_perms(cls, action, model_cls):
        perm_temps = cls.default_action_perms_map.get(action)
        return cls.format_perms(perm_temps, model_cls)

    @staticmethod
    def format_perms(perm_temps, model_cls):
        perms = set()
        for perm_temp in perm_temps:
            perm = perm_temp % {
                'app_label': model_cls._meta.app_label,
                'model_name': model_cls._meta.model_name
            }
            perms.add(perm)
        return perms

    def get_action_required_permissions(self, action, model_cls, view):
        action_perms_map = self.get_action_perms_map(view)

        if action not in action_perms_map:
            raise exceptions.PermissionDenied()
        perms = action_perms_map[action]
        return self.format_perms(perms, model_cls)

    def get_method_required_permissions(self, method, model_cls):
        """
        Given a model and an HTTP method, return the list of permission
        codes that the user is required to have.
        """
        perms_map = self.get_method_perms_map()

        if method not in perms_map:
            raise exceptions.MethodNotAllowed(method)

        model_cls = self._queryset.model
        return self.format_perms(perms_map[method], model_cls)

    def has_permission(self, request, view):
        # Workaround to ensure DjangoModelPermissions are not applied
        # to the root view when using DefaultRouter.
        if getattr(view, '_ignore_rbac_permissions', False):
            return True

        if request.user.is_anonymous and self.authenticated_users_only:
            return False

        if not request.user:
            return False

        action = getattr(view, 'action', None)

        if action == 'metadata':
            return True

        try:
            queryset = self._queryset(view)
            model_cls = queryset.model
        except AssertionError:
            model_cls = None
        if action:
            perms = self.get_action_required_permissions(view.action, model_cls, view)
        else:
            perms = self.get_required_permissions(request.method, model_cls)
        return request.user.has_perms(perms)

