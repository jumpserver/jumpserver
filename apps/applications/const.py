#  coding: utf-8
#
from django.db import models
from django.utils.translation import ugettext_lazy as _


class AppCategory(models.TextChoices):
    db = 'db', _('Database')
    remote_app = 'remote_app', _('Remote app')
    cloud = 'cloud', 'Cloud'

    @classmethod
    def get_label(cls, category):
        return dict(cls.choices).get(category, '')

    @classmethod
    def is_xpack(cls, category):
        return category in ['remote_app']


class AppType(models.TextChoices):
    # db category
    mysql = 'mysql', 'MySQL'
    mariadb = 'mariadb', 'MariaDB'
    oracle = 'oracle', 'Oracle'
    pgsql = 'postgresql', 'PostgreSQL'
    sqlserver = 'sqlserver', 'SQLServer'
    redis = 'redis', 'Redis'
    mongodb = 'mongodb', 'MongoDB'

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
            AppCategory.db: [
                cls.mysql, cls.mariadb, cls.oracle, cls.pgsql,
                cls.sqlserver, cls.redis, cls.mongodb
            ],
            AppCategory.remote_app: [
                cls.chrome, cls.mysql_workbench,
                cls.vmware_client, cls.custom
            ],
            AppCategory.cloud: [cls.k8s]
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
        return [tp.value for tp in cls.category_types_mapper()[AppCategory.db]]

    @classmethod
    def remote_app_types(cls):
        return [tp.value for tp in cls.category_types_mapper()[AppCategory.remote_app]]

    @classmethod
    def cloud_types(cls):
        return [tp.value for tp in cls.category_types_mapper()[AppCategory.cloud]]

    @classmethod
    def is_xpack(cls, tp):
        tp_category_mapper = cls.type_category_mapper()
        category = tp_category_mapper[tp]

        if AppCategory.is_xpack(category):
            return True
        return tp in ['oracle', 'postgresql', 'sqlserver']
