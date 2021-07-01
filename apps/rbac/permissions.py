from rest_framework import permissions, exceptions
from orgs.utils import current_org


class RBACPermission(permissions.DjangoModelPermissions):

    def get_perms_map(self):

        perms_map = self.perms_map

        for method, perms in perms_map.items():
            for i, perm in enumerate(perms):
                perms[i] = f'%(scope)s.{perm}'

        return self.perms_map

    def get_perms_scope(self):
        scope = 'org:{org_id}'.format(org_id=current_org.id)
        return scope

    def get_required_permissions(self, method, model_cls):
        """
        Given a model and an HTTP method, return the list of permission
        codes that the user is required to have.
        """
        # app-label.action_model-name
        # users.add_user
        # system:|app-label.action_model-name

        kwargs = {
            'scope': self.get_perms_scope(),
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }

        perms_map = self.get_perms_map()

        if method not in perms_map:
            raise exceptions.MethodNotAllowed(method)

        return [perm % kwargs for perm in perms_map[method]]

    def has_perm(self, perm, obj):
        # org:org-id.app-label.action_model-name
        # org:org-id|safe:safe-id.app-label.action_model-name
        if 'system':
            pass
        if 'org':
            pass
        if 'safe':
            pass
