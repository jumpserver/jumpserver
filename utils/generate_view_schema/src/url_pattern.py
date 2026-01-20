from .view import CustomView

__all__ = ['CustomURLPattern']


class CustomURLPattern:
    def __init__(self, raw, prefix='/'):
        self.raw = raw
        self.prefix = prefix
        self.full_path = f'{self.prefix}{self.raw.pattern}'
        self.view = CustomView(view_func=self.raw.callback)

    def __str__(self):
        s = f'{self.full_path} -> {self.view.view_path}'
        return s

    def __repr__(self):
        return self.__str__()

