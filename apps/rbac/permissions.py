from rest_framework import permissions, exceptions
from orgs.utils import current_org


class RBACPermission(permissions.DjangoModelPermissions):

    def get_perms_map(self):
        return self.perms_map

    @staticmethod
    def get_perms_scope():
        return 'org:{org_id}'.format(org_id=current_org.id)

    def get_required_permissions(self, method, model_cls):
        """
        Given a model and an HTTP method, return the list of permission
        codes that the user is required to have.
        """
        # scope.app-label.action_model-name
        # org:00000000-0000-0000-0000-000000000000.assets.add_asset
        perms_map = self.get_perms_map()

        if method not in perms_map:
            raise exceptions.MethodNotAllowed(method)

        kwargs = {
            'scope': self.get_perms_scope(),
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }
        return [f'%(scope)s.{perm}' % kwargs for perm in perms_map[method]]
