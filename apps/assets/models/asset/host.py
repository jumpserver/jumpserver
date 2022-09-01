from assets.const import Category
from .common import Asset


class Host(Asset):
    def save(self, *args, **kwargs):
        self.category = Category.HOST
        return super().save(*args, **kwargs)
