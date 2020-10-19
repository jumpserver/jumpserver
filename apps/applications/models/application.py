from itertools import chain

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_mysql.models import JSONField, QuerySet

from orgs.mixins.models import OrgModelMixin
from common.mixins import CommonModelMixin
from common.db.models import ChoiceSet


class DBType(ChoiceSet):
    mysql = 'mysql', 'MySQL'
    oracle = 'oracle', 'Oracle'
    pgsql = 'postgresql', 'PostgreSQL'
    mariadb = 'mariadb', 'MariaDB'

    @classmethod
    def get_type_serializer_cls_mapper(cls):
        from ..serializers import database_app
        mapper = {
            cls.mysql: database_app.MySQLAttrsSerializer,
            cls.oracle: database_app.OracleAttrsSerializer,
            cls.pgsql: database_app.PostgreAttrsSerializer,
            cls.mariadb: database_app.MariaDBAttrsSerializer,
        }
        return mapper


class RemoteAppType(ChoiceSet):
    chrome = 'chrome', 'Chrome'
    mysql_workbench = 'mysql_workbench', 'MySQL Workbench'
    vmware_client = 'vmware_client',  'vSphere Client'
    custom = 'custom', _('Custom')

    @classmethod
    def get_type_serializer_cls_mapper(cls):
        from ..serializers import remote_app
        mapper = {
            cls.chrome: remote_app.ChromeAttrsSerializer,
            cls.mysql_workbench: remote_app.MySQLWorkbenchAttrsSerializer,
            cls.vmware_client: remote_app.VMwareClientAttrsSerializer,
            cls.custom: remote_app.CustomRemoteAppAttrsSeralizers,
        }
        return mapper


class CloudType(ChoiceSet):
    k8s = 'k8s', 'Kubernetes'

    @classmethod
    def get_type_serializer_cls_mapper(cls):
        from ..serializers import k8s_app
        mapper = {
            cls.k8s: k8s_app.K8sAttrsSerializer,
        }
        return mapper


class Category(ChoiceSet):
    db = 'db', _('Database')
    remote_app = 'remote_app', _('Remote app')
    cloud = 'cloud', 'Cloud'

    @classmethod
    def get_category_type_mapper(cls):
        return {
            cls.db: DBType,
            cls.remote_app: RemoteAppType,
            cls.cloud: CloudType
        }

    @classmethod
    def get_category_type_choices_mapper(cls):
        return {
            name: tp.choices
            for name, tp in cls.get_category_type_mapper().items()
        }

    @classmethod
    def get_type_choices(cls, category):
        return cls.get_category_type_choices_mapper().get(category, [])

    @classmethod
    def get_all_type_choices(cls):
        all_grouped_choices = tuple(cls.get_category_type_choices_mapper().values())
        return tuple(chain(*all_grouped_choices))

    @classmethod
    def get_all_type_serializer_mapper(cls):
        mapper = {}
        for tp in cls.get_category_type_mapper().values():
            mapper.update(tp.get_type_serializer_cls_mapper())
        return mapper

    @classmethod
    def get_type_serializer_cls(cls, tp):
        mapper = cls.get_all_type_serializer_mapper()
        return mapper.get(tp, None)


class Application(CommonModelMixin, OrgModelMixin):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    domain = models.ForeignKey('assets.Domain', on_delete=models.SET_NULL, null=True)
    category = models.CharField(max_length=16, choices=Category.choices, verbose_name=_('Category'))
    type = models.CharField(max_length=16, choices=Category.get_all_type_choices(), verbose_name=_('Type'))
    attrs = JSONField()
    comment = models.TextField(
        max_length=128, default='', blank=True, verbose_name=_('Comment')
    )
    objects = QuerySet.as_manager()

    class Meta:
        unique_together = [('org_id', 'name')]
        ordering = ('name',)
