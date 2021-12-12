import copy

from django.db.models import Model
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from common.exceptions import JMSException
from common.utils import get_logger
from .api import PamAPi
from ..base import BaseSecretClient
from .adapter.exceptions import InvalidRequest

logger = get_logger(__name__)


class PamSecretClient(BaseSecretClient):

    def __init__(self, instance: Model):
        super().__init__(instance)
        self.client = PamAPi(
            settings.PAM_URL,
            username=settings.PAM_USERNAME,
            password=settings.PAM_PASSWORD
        )
        if not self.client.is_active:
            raise JMSException(
                code='init_pam_fail',
                detail=_('Initialization pam fail')
            )

        self.department_id = self.client.read_department_id(self.org.name)

    @property
    def org(self):
        from orgs.models import Organization
        return Organization.get_instance(self.instance.org_id, default=Organization.root())

    @property
    def protocol(self):
        if hasattr(self.instance, 'protocol'):
            return self.instance.protocol
        else:
            if self.instance.systemuser:
                return self.instance.systemuser.protocol
            if hasattr(self.instance, 'asset'):
                return self.instance.asset.protocol
            elif hasattr(self.instance, 'app'):
                return self.instance.app.type

    @property
    def account_name(self):
        if not self.is_default:
            username = self.instance.get_or_systemuser_attr('username')
            name = self.instance.get_or_systemuser_attr('name')
            setattr(self.instance, 'username', username)
            setattr(self.instance, 'name', name)

        username = self.instance.username
        name = self.instance.name
        return self.client.package_account_name(username, name)

    @property
    def dev_name(self):
        if self.is_default:
            dev_name = self.client.package_dev_name(
                self.org.name, self.protocol, self.org.name
            )
        else:
            if hasattr(self.instance, 'asset'):
                dev_name = self.instance.asset.hostname
            elif hasattr(self.instance, 'app'):
                dev_name = self.instance.app.name
            else:
                raise JMSException()
            dev_name = self.client.package_dev_name(
                self.org.name, self.protocol, name=dev_name
            )

        return dev_name

    @property
    def dev_type_id(self):
        return self.client.read_dev_type_id(self.protocol)

    @property
    def ip(self):
        ip = '1'
        if hasattr(self.instance, 'asset'):
            ip = self.instance.asset.ip
        elif hasattr(self.instance, 'app'):
            ip = self.instance.app.attrs.get('host', '1')
        return ip

    def get_services(self, protocol):
        services = self.client.DEV_TYPE_MAP[protocol]['services']
        if not self.is_default and self.client.DEV_TYPE_MAP[protocol]['sysTypeGroup'] == 'Database':
            services = copy.deepcopy(services)
            app = self.instance.app
            database = app.attrs.get('database')
            port = app.attrs.get('port')
            for k, v in services['services']['services'].items():
                if k == 'Oracle':
                    v['service_name'] = database
                    v['port'] = port if port else v['port']
                else:
                    v['database'] = database
                    v['port'] = port if port else v['port']

        return services

    @property
    def dev_id(self):
        dev_name = self.dev_name
        protocol = self.protocol
        department_id = self.department_id
        dev_id = self.client.read_dev_id(dev_name, protocol, department_id)
        if not dev_id:
            services = self.get_services(protocol)
            dev_id = self.client.create_dev(
                dev_name, protocol, department_id, ip=self.ip, services=services
            )
        return dev_id

    @property
    def is_default(self):
        from assets.models import AuthBook
        from applications.models import Account
        return not isinstance(self.instance, (AuthBook, Account))

    def create_secret(self, secret_data=None):
        logger.debug(f'Pam is creating {self.instance}')
        if not secret_data:
            secret_data = self.create_secret_data()
        password = secret_data['password']
        # 在默认dev保存当前账号 同时在一个新的机器上创建新的账号（密码）
        self.client.create_or_update_account(self.account_name, self.dev_id, password)

    def patch_secret(self, old_secret_data):
        logger.debug(f'Pam is updating {self.instance}')
        secret_data = self.get_change_secret_data(old_secret_data)
        if secret_data:
            self.client.create_or_update_account(
                self.account_name, self.dev_id, secret_data['password']
            )

    def delete_secret(self):
        logger.debug(f'Pam is deleting {self.instance}')
        self.client.delete_account(self.dev_name, self.account_name)

    def get_secret(self):
        try:
            password = self.client.get_pwd(self.dev_name, self.account_name, self.ip)
        except InvalidRequest as e:
            logger.warning(e)
            password = ''
        return {'password': password}


client = PamSecretClient
