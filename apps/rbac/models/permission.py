from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import Permission as DjangoPermission
from django.contrib.auth.models import ContentType as DjangoContentType

from .. import const

Scope = const.Scope

__all__ = ['Permission', 'ContentType']


class ContentType(DjangoContentType):
    class Meta:
        proxy = True

    @property
    def app_model(self):
        return '%s.%s' % (self.app_label, self.model)


class Permission(DjangoPermission):
    """ 权限类 """
    class Meta:
        proxy = True
        verbose_name = _('Permissions')

    @classmethod
    def to_perms(cls, queryset):
        perms = queryset.values_list(
            'content_type__app_label', 'codename'
        )
        perms = list(set(["%s.%s" % (ct, codename) for ct, codename in perms]))
        return sorted(perms)

    @property
    def app_label_codename(self):
        return '%s.%s' % (self.content_type.app_label, self.codename)

    @classmethod
    def get_define_permissions_q(cls, defines):
        """
        :param defines: [(app, model, codename),]
        :return:
        """
        if not defines:
            return None
        q = Q()

        for define in defines:
            app_label, model, actions, resource, *args = list(define)
            kwargs = {}
            if app_label != '*':
                kwargs['content_type__app_label'] = app_label
            if model != '*':
                kwargs['content_type__model'] = model

            actions_list = [a.strip() for a in actions.split(',')]
            actions_regex = '|'.join(actions_list)
            if actions == '*' and resource == '*':
                pass
            elif actions == '*' and resource != '*':
                kwargs['codename__iregex'] = r'[a-z]+_{}$'.format(resource)
            elif actions != '*' and resource == '*':
                kwargs['codename__iregex'] = r'({})_[a-z]+'.format(actions_regex)
            else:
                kwargs['codename__iregex'] = r'({})_{}$'.format(actions_regex, resource)
            q |= Q(**kwargs)
        return q

    @classmethod
    def clean_permissions(cls, permissions, scope=Scope.system):
        if scope == Scope.org:
            excludes = const.org_exclude_permissions
        else:
            excludes = const.system_exclude_permissions
        q = cls.get_define_permissions_q(excludes)
        if q:
            permissions = permissions.exclude(q)
        return permissions

    @staticmethod
    def create_tree_nodes(permissions, scope, check_disabled=False):
        from ..tree import PermissionTreeUtil
        util = PermissionTreeUtil(permissions, scope, check_disabled)
        return util.create_tree_nodes()

    @classmethod
    def get_permissions(cls, scope):
        permissions = cls.objects.all()
        permissions = cls.clean_permissions(permissions, scope=scope)
        return permissions
