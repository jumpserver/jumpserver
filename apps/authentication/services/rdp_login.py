"""Short-lived, one-use RDP login tickets in the shared Redis cache."""
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import UUID

from django.core.cache import cache
from django.utils import timezone
from django_redis import get_redis_connection
from redis.exceptions import RedisError
from rest_framework.exceptions import APIException


class TicketCacheUnavailable(APIException):
    status_code = 503
    default_detail = 'RDP login ticket cache is unavailable'


@dataclass(frozen=True)
class RDPLoginTicket:
    id: UUID
    connection_id: UUID
    connection_token_id: UUID
    org_id: UUID
    user_id: UUID
    asset_id: UUID
    host_id: UUID
    app_id: UUID
    app_name: str
    username: str
    password_hash: str
    expires_at: datetime


class RDPLoginTicketCache:
    consume_script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        end
        return 0
    """

    @staticmethod
    def key(username):
        return cache.make_key('rdp-login:ticket:' + username)

    @staticmethod
    def client():
        return get_redis_connection('default', write=True)

    def add(self, ticket):
        ttl = math.ceil((ticket.expires_at - timezone.now()).total_seconds() * 1000)
        if ttl <= 0:
            return False
        values = asdict(ticket)
        values['expires_at'] = ticket.expires_at.isoformat()
        encoded = json.dumps(values, default=str, sort_keys=True, separators=(',', ':'))
        try:
            return bool(self.client().set(self.key(ticket.username), encoded, px=ttl, nx=True))
        except RedisError as exc:
            raise TicketCacheUnavailable() from exc

    def get(self, username):
        try:
            encoded = self.client().get(self.key(username))
        except RedisError as exc:
            raise TicketCacheUnavailable() from exc
        if not encoded:
            return None
        try:
            values = json.loads(encoded)
            for field in ('id', 'connection_id', 'connection_token_id', 'org_id',
                          'user_id', 'asset_id', 'host_id', 'app_id'):
                values[field] = UUID(values[field])
            values['expires_at'] = datetime.fromisoformat(values['expires_at'])
            ticket = RDPLoginTicket(**values)
            if ticket.username != username or timezone.is_naive(ticket.expires_at):
                return None
        except (TypeError, ValueError, KeyError):
            return None
        return ticket, encoded

    def consume(self, username, encoded):
        # Validation happens first. Compare-and-delete prevents a second
        # exchange, including requests handled by another Core instance.
        try:
            return bool(self.client().eval(self.consume_script, 1, self.key(username), encoded))
        except RedisError as exc:
            raise TicketCacheUnavailable() from exc
