#  coding: utf-8
#
from collections import defaultdict
from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _


class ApplicationCategoryChoices(TextChoices):
    db = 'db', _('Database')
    remote_app = 'remote_app', _('Remote app')
    cloud = 'cloud', 'Cloud'

    @classmethod
    def get_label(cls, category):
        return dict(cls.choices).get(category, '')


ACC = ApplicationCategoryChoices


class ApplicationTypeChoices(TextChoices):
    # db category
    mysql = 'mysql', 'MySQL'
    oracle = 'oracle', 'Oracle'
    pgsql = 'postgresql', 'PostgreSQL'
    mariadb = 'mariadb', 'MariaDB'

    # remote-app category
    chrome = 'chrome', 'Chrome'
    mysql_workbench = 'mysql_workbench', 'MySQL Workbench'
    vmware_client = 'vmware_client', 'vSphere Client'
    custom = 'custom', _('Custom')

    # cloud category
    k8s = 'k8s', 'Kubernetes'

    @classmethod
    def category_types_mapper(cls):
        return {
            ACC.db: [cls.mysql, cls.oracle, cls.pgsql, cls.mariadb],
            ACC.remote_app: [cls.chrome, cls.mysql_workbench, cls.vmware_client, cls.custom],
            ACC.cloud: [cls.k8s]
        }

    @classmethod
    def type_category_mapper(cls):
        mapper = {}
        for category, tps in cls.category_types_mapper().items():
            for tp in tps:
                mapper[tp] = category
        return mapper

    @classmethod
    def get_label(cls, tp):
        return dict(cls.choices).get(tp, '')

    @classmethod
    def db_types(cls):
        return [tp.value for tp in cls.category_types_mapper()[ACC.db]]

    @classmethod
    def remote_app_types(cls):
        return [tp.value for tp in cls.category_types_mapper()[ACC.remote_app]]

    @classmethod
    def cloud_types(cls):
        return [tp.value for tp in cls.category_types_mapper()[ACC.cloud]]




