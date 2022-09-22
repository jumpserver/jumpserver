from common.decorator import Singleton
from django.core.cache import cache
from django.conf import settings
from applications.const import AppCategory
from applications.models import Application
from common.utils import get_logger
from common.utils import get_object_or_none


logger = get_logger(__file__)


@Singleton
class DBPortManager(object):
    """ 管理端口-数据库ID的映射, Magnus 要使用 """

    CACHE_KEY = 'PORT_DB_MAPPER'

    def __init__(self):
        self.port_start = settings.MAGNUS_DB_PORTS_START
        self.port_limit = settings.MAGNUS_DB_PORTS_LIMIT_COUNT
        self.port_end = self.port_start + self.port_limit + 1
        # 可以使用的端口列表
        self.all_usable_ports = [i for i in range(self.port_start, self.port_end)]

    def init(self):
        db_ids = Application.objects.filter(category=AppCategory.db).values_list('id', flat=True)
        db_ids = [str(i) for i in db_ids]
        mapper = dict(zip(self.all_usable_ports, list(db_ids)))
        self.set_mapper(mapper)

    def add(self, db: Application):
        mapper = self.get_mapper()
        usable_port = self.get_next_usable_port()
        if not usable_port:
            return False
        mapper.update({usable_port: str(db.id)})
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

    def get_db_by_port(self, port):
        mapper = self.get_mapper()
        db_id = mapper.get(port, None)
        if db_id:
            db = get_object_or_none(Application, id=db_id)
            if not db:
                msg = 'Database not exists, database id: {}'.format(db_id)
            else:
                msg = ''
        else:
            db = None
            msg = 'Port not in port-db mapper, port: {}'.format(port)
        return db, msg

    def get_next_usable_port(self):
        already_use_ports = self.get_already_use_ports()
        usable_ports = list(set(self.all_usable_ports) - set(already_use_ports))
        if len(usable_ports) > 1:
            return usable_ports[0]

        already_use_ports = self.get_already_use_ports()
        msg = 'No port is usable, All usable port count: {}, Already use port count: {}'.format(
            len(self.all_usable_ports), len(already_use_ports)
        )
        logger.warning(msg)

    def get_already_use_ports(self):
        mapper = self.get_mapper()
        return list(mapper.keys())

    def get_mapper(self):
        return cache.get(self.CACHE_KEY, {})

    def set_mapper(self, value):
        """
        value: {
            port: db_id
        }
        """
        cache.set(self.CACHE_KEY, value, timeout=None)


db_port_manager = DBPortManager()
