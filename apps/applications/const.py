#  coding: utf-8
#

from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _


class ApplicationCategoryChoices(TextChoices):
    db = 'db', _('Database')
    remote_app = 'remote_app', _('Remote app')
    cloud = 'cloud', 'Cloud'

    @classmethod
    def get_label(cls, category):
        return dict(cls.choices).get(category, '')


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
    def get_label(cls, tp):
        return dict(cls.choices).get(tp, '')

    @classmethod
    def db_types(cls):
        return [cls.mysql.value, cls.oracle.value, cls.pgsql.value, cls.mariadb.value]

    @classmethod
    def remote_app_types(cls):
        return [cls.chrome.value, cls.mysql_workbench.value, cls.vmware_client.value, cls.custom.value]

    @classmethod
    def cloud_types(cls):
        return [cls.k8s.value]

