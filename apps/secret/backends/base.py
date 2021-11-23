import abc


class BaseSecretClient:
    """
    密钥终端的基类
    """

    def __init__(self, instance):
        self.instance = instance

    @abc.abstractmethod
    def update_or_create_secret(self):
        pass

    @abc.abstractmethod
    def patch_secret(self, old_secret_data):
        pass

    @abc.abstractmethod
    def delete_secret(self):
        pass

    @abc.abstractmethod
    def get_secret(self):
        pass

    def clear_secret(self):
        for secret_field in self.instance.SECRET_FIELD:
            if not hasattr(self.instance, f'_{secret_field}'):
                secret = getattr(self.instance, secret_field)
                setattr(self.instance, f'_{secret_field}', secret)
                setattr(self.instance, secret_field, '')
