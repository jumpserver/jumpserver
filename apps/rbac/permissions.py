from rest_framework import permissions, exceptions

from common.utils import get_logger

logger = get_logger(__name__)


class RBACPermission(permissions.DjangoModelPermissions):
    default_rbac_perms_tmpl = (
        ('list', '%(app_label)s.view_%(model_name)s'),
        ('retrieve', '%(app_label)s.view_%(model_name)s'),
        ('create', '%(app_label)s.add_%(model_name)s'),
        ('update', '%(app_label)s.change_%(model_name)s'),
        ('partial_update', '%(app_label)s.change_%(model_name)s'),
        ('destroy', '%(app_label)s.delete_%(model_name)s'),
        ('bulk_update', '%(app_label)s.change_%(model_name)s'),
        ('partial_bulk_update', '%(app_label)s.change_%(model_name)s'),
        ('bulk_destroy', '%(app_label)s.delete_%(model_name)s'),
        ('render_to_json', '%(app_label)s.add_%(model_name)s'),
        ('metadata', '*'),
        ('GET', '%(app_label)s.view_%(model_name)s'),
        ('OPTIONS', '*'),
        ('HEAD', '%(app_label)s.view_%(model_name)s'),
        ('POST', '%(app_label)s.add_%(model_name)s'),
        ('PUT', '%(app_label)s.change_%(model_name)s'),
        ('PATCH', '%(app_label)s.change_%(model_name)s'),
        ('DELETE', '%(app_label)s.delete_%(model_name)s'),
    )

    # rbac_perms = ((), ())
    # def get_rbac_perms():
    #     return {}

    @staticmethod
    def format_perms(perms_tmpl, model_cls):
        perms = set()
        if not perms_tmpl:
            return perms
        if isinstance(perms_tmpl, str):
            perms_tmpl = [perms_tmpl]
        for perm_tmpl in perms_tmpl:
            perm = perm_tmpl % {
                'app_label': model_cls._meta.app_label,
                'model_name': model_cls._meta.model_name
            }
            perms.add(perm)
        return perms

    @classmethod
    def parse_action_model_perms(cls, action, model_cls):
        perm_tmpl = dict(cls.default_rbac_perms_tmpl).get(action)
        return cls.format_perms(perm_tmpl, model_cls)

    def get_default_action_perms(self, model_cls):
        if model_cls is None:
            return {}

        perms = {}
        for action, tmpl in dict(self.default_rbac_perms_tmpl).items():
            perms[action] = self.format_perms(tmpl, model_cls)
        return perms

    def get_rbac_perms(self, view, model_cls) -> dict:
        if hasattr(view, 'get_rbac_perms'):
            return dict(view.get_rbac_perms())
        perms = {}
        if hasattr(view, 'rbac_perms'):
            perms.update(dict(view.rbac_perms))
        default_perms = self.get_default_action_perms(model_cls)
        if '*' not in perms:
            for k, v in default_perms.items():
                perms.setdefault(k, v)
        return perms

    def _get_action_perms(self, action, model_cls, view):
        action_perms_map = self.get_rbac_perms(view, model_cls)
        if action in action_perms_map:
            perms = action_perms_map[action]
        elif '*' in action_perms_map:
            perms = action_perms_map['*']
        else:
            msg = 'Action not allowed: {}, only `{}` supported'.format(
                action, ','.join(list(action_perms_map.keys()))
            )
            logger.error(msg)
            raise exceptions.PermissionDenied(msg)
        return perms

    def get_model_cls(self, view):
        if hasattr(view, 'perm_model'):
            return getattr(view, 'perm_model')

        try:
            queryset = self._queryset(view)
            if isinstance(queryset, list) and queryset:
                model_cls = queryset[0].__class__
            else:
                model_cls = queryset.model
        except AssertionError as e:
            # logger.error(f'Error get model cls: {e}')
            model_cls = None
        except AttributeError as e:
            # logger.error(f'Error get model cls: {e}')
            model_cls = None
        except Exception as e:
            # logger.error('Error get model class: {} of {}'.format(e, view))
            raise e
        return model_cls

    def get_require_perms(self, request, view):
        """
        获取 request, view 需要的 perms
        :param request:
        :param view:
        :return:
        """
        model_cls = self.get_model_cls(view)
        action = getattr(view, 'action', None)
        if not action:
            action = request.method
        perms = self._get_action_perms(action, model_cls, view)
        return perms

    def has_permission(self, request, view):
        # Workaround to ensure DjangoModelPermissions are not applied
        # to the root view when using DefaultRouter.
        if getattr(view, '_ignore_rbac_permissions', False):
            return True
        if not request.user:
            return False
        if request.user.is_anonymous and self.authenticated_users_only:
            return False

        raw_action = getattr(view, 'raw_action', request.method)
        if raw_action in ['metadata', 'OPTIONS']:
            return True

        perms = self.get_require_perms(request, view)
        if isinstance(perms, str):
            perms = [perms]
        has = request.user.has_perms(perms)
        logger.debug('Api require perms: {}, result: {}'.format(perms, has))
        return has

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
