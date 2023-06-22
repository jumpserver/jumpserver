from abc import ABCMeta, abstractmethod

from django.db.models import Model
from django.forms.models import model_to_dict


class BaseVaultClient:
    __metaclass__ = ABCMeta

    def __init__(self, instance: Model):
        self.instance = instance

    @staticmethod
    @abstractmethod
    def is_active(*args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def create(self):
        raise NotImplementedError

    @abstractmethod
    def update(self):
        raise NotImplementedError

    @abstractmethod
    def delete(self):
        raise NotImplementedError

    @abstractmethod
    def get(self):
        raise NotImplementedError

    @abstractmethod
    def set_secret(self, value):
        raise NotImplementedError

    @abstractmethod
    def sync_basic_info(self):
        raise NotImplementedError

    def get_instance_basic_info(self):
        instance_data = model_to_dict(
            self.instance, exclude=['id']
        )
        data = {}
        for field, value in instance_data.items():
            if not value:
                continue
            data[field] = str(value)
        return data

    def clear_local_secret(self):
        self.instance.is_sync_secret = False
        self.instance._secret = None
        self.instance.save()