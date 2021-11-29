from abc import ABCMeta, abstractmethod


class BaseSecretClient(object):
    """
    密钥终端的基类
    """
    __metaclass__ = ABCMeta

    def __init__(self, instance):
        self.instance = instance

    @abstractmethod
    def update_or_create_secret(self):
        raise NotImplementedError

    @abstractmethod
    def patch_secret(self, old_secret_data):
        raise NotImplementedError

    @abstractmethod
    def delete_secret(self):
        raise NotImplementedError

    @abstractmethod
    def get_secret(self):
        raise NotImplementedError

    def create_secret_data(self):
        instance = self.instance
        fields = getattr(instance, 'SECRET_FIELD')
        secret_data = {
            k: getattr(instance, f'_{k}') for k in fields
        }
        return secret_data

    def clear_secret(self):
        for secret_field in self.instance.SECRET_FIELD:
            if not hasattr(self.instance, f'_{secret_field}'):
                secret = getattr(self.instance, secret_field)
                setattr(self.instance, f'_{secret_field}', secret)
                setattr(self.instance, secret_field, '')
