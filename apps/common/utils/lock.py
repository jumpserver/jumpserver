from uuid import uuid4

from django.core.cache import cache
from django.db.transaction import atomic
from rest_framework.request import Request
from rest_framework.exceptions import NotAuthenticated

from functools import wraps

from orgs.utils import current_org
from common.exceptions import SomeoneIsDoingThis, Timeout
from common.utils.timezone import dt_formater, now
from common.const.distributed_lock_key import ASSETS_UPDATE_NODE_TREE_KEY

client = cache.client.get_client(write=True)

# KEYS[1]： doingkey
# ARGV[1]: doingvalue
# ARGV[2]: commitingvalue
# ARGV[3]: timeout
commiting_lock_script = '''
if redis.call("get", KEYS[1]) == ARGV[1]
then
    return redis.call("set", KEYS[1], ARGV[2], "EX", ARGV[3], "XX")
else
    return 0
end
'''
commiting_lock_fun = client.register_script(commiting_lock_script)


def change_lock_state_to_commiting(key, doingvalue, commitingvalue, timeout):
    return bool(commiting_lock_fun(keys=(key,), args=(doingvalue, commitingvalue, timeout)))


unlock_script = '''
if (redis.call("get",KEYS[1]) == ARGV[1] or redis.call("get",KEYS[1]) == ARGV[2])
then
    return redis.call("del",KEYS[1])
else
    return 0
end
'''
unlock_fun = client.register_script(unlock_script)


def unlock(key, value1, value2):
    return unlock_fun(keys=(key,), args=(value1, value2))


VALUE_TEMPLATE = '{stage}:{username}:{user_id}:{now}:{rand_str}'

DOING = 'doing'
COMMITING = 'commiting'


def _generate_value(request: Request, stage=DOING):
    # 不支持匿名用户
    user = request.user
    if user.is_anonymous:
        raise NotAuthenticated

    return VALUE_TEMPLATE.format(
        stage=stage, username=user.username, user_id=user.id,
        now=dt_formater(now()), rand_str=uuid4()
    )


default_wait_msg = SomeoneIsDoingThis.default_detail


def with_distributed_lock(key, timeout=60, wait_msg=default_wait_msg):
    def decorator(fun):
        @wraps(fun)
        def wrapper(self, request, *args, **kwargs):
            _key = key.format(org_id=current_org.id)
            doing_value = _generate_value(request)
            commiting_value = _generate_value(request, stage=COMMITING)
            try:
                lock = cache.set(_key, doing_value, timeout=timeout, nx=True)
                if not lock:
                    raise SomeoneIsDoingThis(detail=wait_msg)
                with atomic(savepoint=False):
                    ret = fun(self, request, *args, **kwargs)
                    # 提交事务前，检查一下锁是否还在
                    # 锁在的话，更新锁的状态为 `commiting`，延长锁时间，确保事务提交
                    # 锁不在的话回滚
                    ok = change_lock_state_to_commiting(_key, doing_value, commiting_value, timeout)
                    if not ok:
                        # 超时或者被中断了
                        raise Timeout
                    return ret
            finally:
                # 释放锁，锁的两个值都要尝试，不确定异常是从什么位置抛出的
                unlock(_key, commiting_value, doing_value)
