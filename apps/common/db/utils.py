from contextlib import contextmanager

from django.db import connections, transaction, connection
from django.utils.encoding import force_str

from common.utils import get_logger, signer, crypto

logger = get_logger(__file__)


def default_ip_group():
    return ["*"]


def get_object_if_need(model, pk):
    if not isinstance(pk, model):
        try:
            return model.objects.get(id=pk)
        except model.DoesNotExist as e:
            logger.error(f"DoesNotExist: <{model.__name__}:{pk}> not exist")
            raise e
    return pk


def get_objects_if_need(model, pks):
    if not pks:
        return pks
    if not isinstance(pks[0], model):
        objs = list(model.objects.filter(id__in=pks))
        if len(objs) != len(pks):
            pks = set(pks)
            exists_pks = {o.id for o in objs}
            not_found_pks = ",".join(pks - exists_pks)
            logger.error(f"DoesNotExist: <{model.__name__}: {not_found_pks}>")
        return objs
    return pks


def get_objects(model, pks):
    if not pks:
        return pks

    objs = list(model.objects.filter(id__in=pks))
    if len(objs) != len(pks):
        pks = set(pks)
        exists_pks = {o.id for o in objs}
        not_found_pks = pks - exists_pks
        logger.error(f"DoesNotExist: <{model.__name__}: {not_found_pks}>")
    return objs


# 复制 django.db.close_old_connections, 因为它没有导出，ide 提示有问题
def close_old_connections(**kwargs):
    for conn in connections.all(initialized_only=True):
        conn.close_if_unusable_or_obsolete()


# 这个要是在 Django 请求周期外使用的，不能影响 Django 的事务管理， 在 api 中使用会影响 api 事务
@contextmanager
def safe_db_connection():
    close_old_connections()
    yield
    close_old_connections()


@contextmanager
def safe_atomic_db_connection(auto_close=False):
    """
    通用数据库连接管理器（线程安全、事务感知）：
    - 在连接不可用时主动重建连接
    - 在非事务环境下自动关闭连接（可选）
    - 不影响 Django 请求/事务周期
    """
    in_atomic = connection.in_atomic_block  # 当前是否在事务中
    autocommit = transaction.get_autocommit()
    recreated = False

    try:
        if not connection.is_usable():
            connection.close()
            connection.connect()
            recreated = True
        yield
    finally:
        # 只在非事务、autocommit 模式下，才考虑主动清理连接
        if auto_close or (recreated and not in_atomic and autocommit):
            close_old_connections()


@contextmanager
def open_db_connection(alias="default"):
    connection = transaction.get_connection(alias)
    try:
        connection.connect()
        with transaction.atomic():
            yield connection
    finally:
        connection.close()


class Encryptor:
    def __init__(self, value):
        self.value = force_str(value)

    def decrypt(self):
        plain_value = crypto.decrypt(self.value)

        # 如果没有解开，使用原来的signer解密
        if not plain_value:
            plain_value = signer.unsign(self.value) or ""
        return plain_value

    def encrypt(self):
        return crypto.encrypt(self.value)
