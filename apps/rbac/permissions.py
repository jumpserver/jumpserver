from rest_framework import permissions, exceptions
from orgs.utils import current_org


class RBACPermission(permissions.DjangoModelPermissions):

    def get_perms_map(self):
        return self.perms_map

    def get_required_permissions(self, method, model_cls):
        """
        Given a model and an HTTP method, return the list of permission
        codes that the user is required to have.
        """
        # scope|app-label.action_model-name
        # org:00000000-0000-0000-0000-000000000002|assets.add_asset
        perms_map = self.get_perms_map()

        if method not in perms_map:
            raise exceptions.MethodNotAllowed(method)

        perms = []
        for perm in perms_map[method]:
            _perm = perm % {model_cls._meta.app_label, model_cls._meta.model_name}
            if not current_org.is_root():
                _perm = f'org:{current_org.org_id}|{_perm}'
            perms.append(_perm)

        return perms
