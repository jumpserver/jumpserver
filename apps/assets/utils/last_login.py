from datetime import datetime, timezone as datetime_timezone

from django.utils import timezone

from common.utils.connection import get_redis_client
from common.utils import get_logger

WINDOW_SECONDS = 10     # 合并窗口时间
BATCH_SIZE = 1000       # 最大work数量
LATEST_KEY = '{asset:last_login}:latest'
DUE_KEY = '{asset:last_login}:due'
logger = get_logger(__name__)

ENQUEUE_SCRIPT = """
local current = redis.call('HGET', KEYS[1], ARGV[1])
if not current or tonumber(ARGV[2]) > tonumber(current) then
    redis.call('HSET', KEYS[1], ARGV[1], ARGV[2])
end
redis.call('ZADD', KEYS[2], 'NX', ARGV[3], ARGV[1])
return 1
"""

GET_DUE_SCRIPT = """
local members = redis.call(
    'ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1],
    'LIMIT', 0, ARGV[2]
)
local result = {}
for _, member in ipairs(members) do
    local value = redis.call('HGET', KEYS[2], member)
    if value then
        table.insert(result, member)
        table.insert(result, value)
    end
end
return result
"""

ACK_SCRIPT = """
for index = 2, #ARGV, 2 do
    local member = ARGV[index]
    local processed = ARGV[index + 1]
    local current = redis.call('HGET', KEYS[1], member)
    if current == processed then
        redis.call('HDEL', KEYS[1], member)
        redis.call('ZREM', KEYS[2], member)
    elseif current then
        redis.call('ZADD', KEYS[2], ARGV[1], member)
    end
end
return 1
"""


class AssetLastLoginBuffer:
    def __init__(self, redis=None):
        self._redis = redis

    @property
    def redis(self):
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis

    def enqueue(self, asset_id, login_at):
        asset_id = str(asset_id)
        due_at = timezone.now().timestamp() + WINDOW_SECONDS
        self.redis.eval(
            ENQUEUE_SCRIPT,
            2,
            LATEST_KEY,
            DUE_KEY,
            asset_id,
            login_at.timestamp(),
            due_at,
        )

    def get_due(self, now=None, batch_size=BATCH_SIZE):
        now = now or timezone.now()
        values = self.redis.eval(
            GET_DUE_SCRIPT,
            2,
            DUE_KEY,
            LATEST_KEY,
            now.timestamp(),
            batch_size,
        )
        updates = {}
        for index in range(0, len(values), 2):
            asset_id = values[index].decode()
            timestamp = float(values[index + 1].decode())
            updates[asset_id] = datetime.fromtimestamp(
                timestamp, tz=datetime_timezone.utc
            )
        return updates

    def ack(self, updates, now=None):
        if not updates:
            return
        now = now or timezone.now()
        args = [now.timestamp() + WINDOW_SECONDS]
        for asset_id, date_last_login in updates.items():
            args.extend([asset_id, date_last_login.timestamp()])
        self.redis.eval(
            ACK_SCRIPT,
            2,
            LATEST_KEY,
            DUE_KEY,
            *args,
        )


asset_last_login_buffer = AssetLastLoginBuffer()


def enqueue_asset_last_login(asset_id, login_at):
    try:
        asset_last_login_buffer.enqueue(asset_id, login_at)
    except Exception:
        logger.exception(
            'Failed to enqueue asset last login update: %s', asset_id
        )
