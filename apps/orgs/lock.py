from uuid import uuid4
from functools import wraps

from django.core.cache import cache
from django.db.transaction import atomic
from rest_framework.request import Request
from rest_framework.exceptions import NotAuthenticated

from orgs.utils import current_org
from common.exceptions import SomeoneIsDoingThis, Timeout
from common.utils.timezone import dt_formater, now

# Redis 中锁值得模板，该模板提供了很强的可读性，方便调试与排错
VALUE_TEMPLATE = '{stage}:{username}:{user_id}:{now}:{rand_str}'

# 锁的状态
DOING = 'doing'  # 处理中，此状态的锁可以被干掉
COMMITING = 'commiting'  # 提交事务中，此状态很重要，要确保事务在锁消失之前返回了，不要轻易删除该锁

client = cache.client.get_client(write=True)


"""
将锁的状态从 `doing` 切换到 `commiting`
KEYS[1]： key
ARGV[1]: doingvalue
ARGV[2]: commitingvalue
ARGV[3]: timeout
"""
change_lock_state_to_commiting_lua = '''
if (redis.call("get", KEYS[1]) == ARGV[1])
then
    return redis.call("set", KEYS[1], ARGV[2], "EX", ARGV[3], "XX")
else
    return 0
end
'''
change_lock_state_to_commiting_lua_obj = client.register_script(change_lock_state_to_commiting_lua)


"""
释放锁，两种`value`都要检查`doing`和`commiting`
KEYS[1]： key
ARGV[1]: 两个 `value` 中的其中一个
ARGV[2]: 两个 `value` 中的其中一个
"""
release_lua = '''
if (redis.call("get",KEYS[1]) == ARGV[1] or redis.call("get",KEYS[1]) == ARGV[2])
then
    return redis.call("del",KEYS[1])
else
    return 0
end
'''
release_lua_obj = client.register_script(release_lua)


def acquire(key, value, timeout):
    return client.set(key, value, ex=timeout, nx=True)


def get(key):
    return client.get(key)


def change_lock_state_to_commiting(key, doingvalue, commitingvalue, timeout=600):
    # 将锁的状态从 `doing` 切换到 `commiting`
    return bool(change_lock_state_to_commiting_lua_obj(keys=(key,), args=(doingvalue, commitingvalue, timeout)))


def release(key, value1, value2):
    # 释放锁，两种`value` `doing`和`commiting` 都要检查
    return release_lua_obj(keys=(key,), args=(value1, value2))


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


def org_level_transaction_lock(key, timeout=300, wait_msg=default_wait_msg):
    """
    被装饰的 `View` 必须取消自身的 `ATOMIC_REQUESTS`，因为该装饰器要有事务的完全控制权
    [官网](https://docs.djangoproject.com/en/3.1/topics/db/transactions/#tying-transactions-to-http-requests)

    1. 获取锁：只有当锁对应的 `key` 不存在时成功获取，`value` 设置为 `doing`
    2. 开启事务：本次请求的事务必须确保在这里开启
    3. 执行 `View` 体
    4. `View` 体执行结束未异常，此时事务还未提交
    5. 检查锁是否过时，过时事务回滚，不过时，重新设置`key`延长`key`有效期，已确保足够时间提交事务，同时把`key`的状态改为`commiting`
    6. 提交事务
    7. 释放锁，释放的时候会检查`doing`与`commiting`的值，因为删除或者更改锁必须提供与当前锁的`value`相同的值，确保不误删
       [锁参考文章](http://doc.redisfans.com/string/set.html#id2)
    """

    def decorator(fun):
        @wraps(fun)
        def wrapper(request, *args, **kwargs):
            # `key`可能是组织相关的，如果是把组织`id`加上
            _key = key.format(org_id=current_org.id)
            doing_value = _generate_value(request)
            commiting_value = _generate_value(request, stage=COMMITING)
            try:
                lock = acquire(_key, doing_value, timeout)
                if not lock:
                    raise SomeoneIsDoingThis(detail=wait_msg)
                with atomic(savepoint=False):
                    ret = fun(request, *args, **kwargs)
                    # 提交事务前，检查一下锁是否还在
                    # 锁在的话，更新锁的状态为 `commiting`，延长锁时间，确保事务提交
                    # 锁不在的话回滚
                    ok = change_lock_state_to_commiting(_key, doing_value, commiting_value)
                    if not ok:
                        # 超时或者被中断了
                        raise Timeout
                    return ret
            finally:
                # 释放锁，锁的两个值都要尝试，不确定异常是从什么位置抛出的
                release(_key, commiting_value, doing_value)
        return wrapper
    return decorator
