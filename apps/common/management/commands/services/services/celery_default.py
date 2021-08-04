from .celery_base import CeleryBaseService

__all__ = ['CeleryDefaultService']


class CeleryDefaultService(CeleryBaseService):

    def __init__(self):
        super().__init__(name=self.Services.celery_default.value, num=10, queue='celery')

