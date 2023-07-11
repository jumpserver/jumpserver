import sys
from abc import ABC
from common.utils.timezone import as_current_tz
from common.db.utils import Encryptor

current_module = sys.modules[__name__]

__all__ = ['build_entry']


class BaseEntry(ABC):

    def __init__(self, instance):
        self.instance = instance

    def get_histories(self):
        return []


class AccountEntry(BaseEntry):

    def get_histories(self):
        from accounts.serializers import AccountHistorySerializer
        account = self.instance
        histories = account.history.all()

        history = account.history.first()
        if not history:
            return []

        if (account.secret == history.secret) and (account.secret_type == history.secret_type):
            histories = histories.exclude(history_id=history.history_id)

        data = []
        for h in histories:
            _serializer = AccountHistorySerializer(instance=h)
            _data = _serializer.data
            secret = getattr(h, '_secret', '')
            _data.update({
                'secret': Encryptor(secret).decrypt()
            })
            data.append(_data)
        return data


class AccountTemplateEntry(BaseEntry):
    pass


class AccountHistoricalRecordsEntry(BaseEntry):
    pass


def build_entry(instance) -> BaseEntry:
    class_name = instance.__class__.__name__
    entry_class_name = f'{class_name}Entry'
    entry_class = getattr(current_module, entry_class_name, None)
    if not entry_class:
        raise Exception(f'Entry class {entry_class_name} is not found')
    return entry_class(instance)
