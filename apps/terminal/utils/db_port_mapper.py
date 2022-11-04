from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache
from django.conf import settings

from common.decorator import Singleton
from common.utils import get_logger, get_object_or_none
from common.exceptions import JMSException
from applications.const import AppCategory
from applications.models import Application
from orgs.utils import tmp_to_root_org


logger = get_logger(__file__)


@Singleton
class DBPortManager(object):
    """ 管理端口-数据库ID的映射, Magnus 要使用 """

    CACHE_KEY = 'PORT_DB_MAPPER'

    def __init__(self):
        try:
            port_start, port_end = settings.MAGNUS_PORTS.split('-')
            port_start, port_end = int(port_start), int(port_end)
        except Exception as e:
            logger.error('MAGNUS_PORTS config error: {}'.format(e))
            port_start, port_end = 30000, 30100

        self.port_start, self.port_end = port_start, port_end
        # 可以使用的端口列表
        self.all_available_ports = list(range(self.port_start, self.port_end + 1))

    @property
    def magnus_listen_port_range(self):
        return settings.MAGNUS_PORTS

    def init(self):
        with tmp_to_root_org():
            db_ids = Application.objects.filter(category=AppCategory.db).values_list('id', flat=True)
        db_ids = [str(i) for i in db_ids]
        mapper = dict(zip(self.all_available_ports, list(db_ids)))
        self.set_mapper(mapper)

    def add(self, db: Application):
        mapper = self.get_mapper()
        available_port = self.get_next_available_port()
        mapper.update({available_port: str(db.id)})
        self.set_mapper(mapper)
        return True

    def pop(self, db: Application):
        mapper = self.get_mapper()
        to_delete_port = self.get_port_by_db(db)
        mapper.pop(to_delete_port, None)
        self.set_mapper(mapper)

    def get_port_by_db(self, db):
        mapper = self.get_mapper()
        for port, db_id in mapper.items():
            if db_id == str(db.id):
                return port
        error = _(
            'No available port is matched. '
            'The number of databases may have exceeded the number of ports '
            'open to the database agent service, '
            'Contact the administrator to open more ports.'
        )
        raise JMSException(error)

    def get_db_by_port(self, port):
        try:
            port = int(port)
        except Exception as e:
            raise JMSException('Port type error: {}'.format(e))
        mapper = self.get_mapper()
        db_id = mapper.get(port, None)
        if not db_id:
            raise JMSException('Database not in port-db mapper, port: {}'.format(port))
        with tmp_to_root_org():
            db = get_object_or_none(Application, id=db_id)
        if not db:
            raise JMSException('Database not exists, db id: {}'.format(db_id))
        return db

    def get_next_available_port(self):
        already_use_ports = self.get_already_use_ports()
        available_ports = sorted(list(set(self.all_available_ports) - set(already_use_ports)))
        if len(available_ports) <= 0:
            msg = _('No ports can be used, check and modify the limit on the number '
                    'of ports that Magnus listens on in the configuration file.')
            tips = _('All available port count: {}, Already use port count: {}').format(
                len(self.all_available_ports), len(already_use_ports)
            )
            error = msg + tips
            raise JMSException(error)
        port = available_ports[0]
        logger.debug('Get next available port: {}'.format(port))
        return port

    def get_already_use_ports(self):
        mapper = self.get_mapper()
        return sorted(list(mapper.keys()))

    def get_mapper(self):
        mapper = cache.get(self.CACHE_KEY, {})
        if not mapper:
            # redis 可能被清空，重新初始化一下
            self.init()
        return cache.get(self.CACHE_KEY, {})

    def set_mapper(self, value):
        """
        value: {
            port: db_id
        }
        """
        cache.set(self.CACHE_KEY, value, timeout=None)


db_port_manager = DBPortManager()
