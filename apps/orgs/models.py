from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import ValidationError

from common.db.models import JMSBaseModel
from common.tree import TreeNode
from common.utils import lazyproperty, settings, get_logger

logger = get_logger(__name__)


class OrgRoleMixin:
    ROOT_ID = '00000000-0000-0000-0000-000000000000'
    ROOT_NAME = _('GLOBAL')
    DEFAULT_ID = '00000000-0000-0000-0000-000000000002'
    DEFAULT_NAME = _('DEFAULT')
    SYSTEM_ID = '00000000-0000-0000-0000-000000000004'
    SYSTEM_NAME = _('SYSTEM')
    INTERNAL_IDS = [ROOT_ID, DEFAULT_ID, SYSTEM_ID]
    members: models.Manager
    id: str

    def get_members(self):
        from users.models import User
        if self.id == self.ROOT_ID:
            return User.objects.all().exclude(is_service_account=True)
        else:
            return self.members.all().distinct()

    def add_member(self, user, role=None):
        from rbac.builtin import BuiltinRole
        from .utils import tmp_to_org

        if role:
            role_id = role.id
        elif user.is_service_account:
            role_id = BuiltinRole.system_component.id
        else:
            role_id = BuiltinRole.org_user.id

        with tmp_to_org(self):
            defaults = {
                'user': user, 'role_id': role_id,
                'org_id': self.id, 'scope': 'org'
            }
            self.members.through.objects.update_or_create(**defaults, defaults=defaults)

    def get_origin_role_members(self, role_name):
        from rbac.models import OrgRoleBinding
        from rbac.builtin import BuiltinRole
        from .utils import tmp_to_org

        role_mapper = {
            'user': BuiltinRole.org_user,
            'auditor': BuiltinRole.org_auditor,
            'admin': BuiltinRole.org_admin
        }
        assert role_name in role_mapper
        role = role_mapper.get(role_name).get_role()
        with tmp_to_org(self):
            org_admins = OrgRoleBinding.get_role_users(role)
            return org_admins

    @property
    def admins(self):
        from users.models import User
        admins = self.get_origin_role_members('admin')
        if not admins:
            admins = User.objects.filter(username='admin')
        return admins

    @property
    def auditors(self):
        return self.get_origin_role_members('auditor')

    @property
    def users(self):
        return self.get_origin_role_members('user')


class Organization(OrgRoleMixin, JMSBaseModel):
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Name"))
    builtin = models.BooleanField(default=False, verbose_name=_('Builtin'))
    members = models.ManyToManyField(
        'users.User', related_name='orgs', through='rbac.RoleBinding', through_fields=('org', 'user')
    )

    orgs_mapping = None

    class Meta:
        verbose_name = _("Organization")
        permissions = (
            ('view_rootorg', _('Can view root org')),
            ('view_alljoinedorg', _('Can view all joined org')),
        )

    def __str__(self):
        return str(self.name)

    @classmethod
    def get_instance(cls, id_or_name, default=None):
        assert default is None or isinstance(default, cls), (
            '`default` must be None or `Organization` instance'
        )
        org = cls.get_instance_from_memory(id_or_name)
        org = org or default
        return org

    @classmethod
    def get_instance_from_memory(cls, id_or_name):
        if not isinstance(cls.orgs_mapping, dict):
            cls.orgs_mapping = cls.construct_orgs_mapping()

        org = cls.orgs_mapping.get(str(id_or_name))
        if not org:
            # 内存失效速度慢于读取速度(on_org_create_or_update)
            cls.orgs_mapping = cls.construct_orgs_mapping()

        org = cls.orgs_mapping.get(str(id_or_name))
        return org

    @classmethod
    def construct_orgs_mapping(cls):
        orgs_mapping = {}
        for org in cls.objects.all():
            orgs_mapping[str(org.id)] = org
            orgs_mapping[str(org.name)] = org
        root_org = cls.root()
        orgs_mapping.update({
            root_org.id: root_org,
            'GLOBAL': root_org,
            '全局组织': root_org
        })
        return orgs_mapping

    @classmethod
    def expire_orgs_mapping(cls):
        cls.orgs_mapping = None

    def org_id(self):
        return self.id

    @classmethod
    def get_or_create_builtin(cls, **kwargs):
        _id = kwargs['id']
        org = cls.get_instance(_id)
        if org:
            return org
        org, created = cls.objects.get_or_create(id=_id, defaults=kwargs)
        if created:
            org.builtin = True
            org.save()
        return org

    @classmethod
    def default(cls):
        kwargs = {'id': cls.DEFAULT_ID, 'name': cls.DEFAULT_NAME}
        return cls.get_or_create_builtin(**kwargs)

    @classmethod
    def system(cls):
        kwargs = {'id': cls.SYSTEM_ID, 'name': cls.SYSTEM_NAME}
        return cls.get_or_create_builtin(**kwargs)

    @classmethod
    def root(cls):
        name = settings.GLOBAL_ORG_DISPLAY_NAME or cls.ROOT_NAME
        return cls(id=cls.ROOT_ID, name=name, builtin=True)

    def is_root(self):
        return self.id == self.ROOT_ID

    def is_default(self):
        return str(self.id) == self.DEFAULT_ID

    def is_system(self):
        return str(self.id) == self.SYSTEM_ID

    @property
    def internal(self):
        return str(self.id) in self.INTERNAL_IDS

    def change_to(self):
        from .utils import set_current_org
        set_current_org(self)

    @lazyproperty
    def resource_statistics_cache(self):
        from .caches import OrgResourceStatisticsCache
        return OrgResourceStatisticsCache(self)

    def get_total_resources_amount(self):
        from django.apps import apps
        from orgs.mixins.models import OrgModelMixin
        summary = {'users.Members': self.get_members().count()}
        for app_name, app_config in apps.app_configs.items():
            models_cls = app_config.get_models()
            for model in models_cls:
                if not issubclass(model, OrgModelMixin):
                    continue
                key = '{}.{}'.format(app_name, model.__name__)
                summary[key] = self.get_resource_amount(model)
        return summary

    def get_resource_amount(self, resource_model):
        from .utils import tmp_to_org
        from .mixins.models import OrgModelMixin

        if not issubclass(resource_model, OrgModelMixin):
            return 0
        with tmp_to_org(self):
            return resource_model.objects.all().count()

    def as_tree_node(self, oid, pid, opened=True):
        node = TreeNode(**{
            'id': oid,
            'name': self.name,
            'title': self.name,
            'pId': pid,
            'open': opened,
            'isParent': True,
            'meta': {
                'type': 'org'
            }
        })
        return node

    def delete_related_models(self):
        from orgs.utils import tmp_to_root_org
        from tickets.models import TicketFlow
        with tmp_to_root_org():
            TicketFlow.objects.filter(org_id=self.id).delete()

    def delete(self, *args, **kwargs):
        if str(self.id) in self.INTERNAL_IDS:
            raise ValidationError(_('Can not delete virtual org'))
        self.delete_related_models()
        return super().delete(*args, **kwargs)
