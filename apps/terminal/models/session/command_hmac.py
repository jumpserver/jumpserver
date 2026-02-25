from common.db.hmac import AbstractHmac

__all__ = ['CommandHmac']


class CommandHmac(AbstractHmac):
    HMAC_FIELDS = ['user', 'asset', 'account', 'input', 'session', 'timestamp']

    class Meta(AbstractHmac.Meta):
        db_table = "terminal_command_hmac"
        verbose_name = "Command HMAC"
