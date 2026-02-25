from common.db.hmac import AbstractHmac

__all__ = ['SessionHmac']


class SessionHmac(AbstractHmac):
    HMAC_FIELDS = ['user', 'asset', 'account', 'login_from', 'remote_addr', 'date_start']

    class Meta(AbstractHmac.Meta):
        db_table = "terminal_session_hmac"
        verbose_name = "Session HMAC"
