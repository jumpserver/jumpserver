from django.apps import apps
from django.contrib.auth.models import ContentType as DjangoContentType
from django.contrib.auth.models import Permission as DjangoPermission
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from common.utils import lazyproperty
from .. import const

Scope = const.Scope

__all__ = ['Permission', 'ContentType']


class ContentType(DjangoContentType):
    class Meta:
        proxy = True

    _apps_map = {}

    @property
    def app_model(self):
        return '%s.%s' % (self.app_label, self.model)

    @classmethod
    def apps_map(cls):
        from ..tree import app_nodes_data
        if cls._apps_map:
            return cls._apps_map
        mapper = {}
        for d in app_nodes_data:
            i = d['id']
            name = d.get('name')

            if not name:
                config = apps.get_app_config(d['id'])
                if config:
                    name = config.verbose_name
            if name:
                mapper[i] = name
        cls._apps_map = mapper
        return mapper

    @property
    def app_display(self):
        return self.apps_map().get(self.app_label)

    @lazyproperty
    def fields(self):
        model = self.model_class()
        return model._meta.fields

    @lazyproperty
    def field_names(self):
        return [f.name for f in self.fields]

    @lazyproperty
    def filter_field_names(self):
        names = []
        if 'name' in self.field_names:
            names.append('name')
        if 'address' in self.field_names:
            names.append('address')
        return names

    def filter_queryset(self, queryset, keyword):
        q = Q()
        for name in self.filter_field_names:
            q |= Q(**{name + '__icontains': keyword})
        return queryset.filter(q)


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
