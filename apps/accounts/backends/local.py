from abc import ABC

from common.db.utils import Encryptor
from common.utils import get_logger
from common.utils.timezone import as_current_tz
from .base import BaseVaultClient

logger = get_logger(__name__)

__all__ = ['LocalVaultClient']


class LocalVaultClient(BaseVaultClient, ABC):
    @staticmethod
    def is_active(*args, **kwargs):
        return True

    def create(self):
        pass

    def update(self):
        pass

    def delete(self):
        pass

    def get(self):
        secret = getattr(self.instance, '_secret', '')
        return {'secret': secret}

    def get_history_data(self):
        from accounts.models import Account

        instance = self.instance
        if not isinstance(instance, Account):
            return []

        histories = instance.history.all()
        last_history = instance.history.first()
        if not last_history:
            return []

        if instance.secret == last_history.secret \
                and instance.secret_type == last_history.secret_type:
            histories = histories.exclude(history_id=last_history.history_id)
        data = []
        for i in histories:
            history_date = as_current_tz(i.history_date)
            history_date = history_date.strftime('%Y-%m-%d %H:%M:%S')
            secret = getattr(i, '_secret', '')
            data.append({
                'id': str(i.id),
                'version': str(i.version),
                'history_date': history_date,
                'secret': Encryptor(secret).decrypt(),
            })
        return data

    def _sync_basic_info(self, info):
        pass
