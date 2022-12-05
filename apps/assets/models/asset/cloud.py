
from .common import Asset


class Cloud(Asset):
    def __str__(self):
        return self.name
