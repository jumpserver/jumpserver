from .celery_base import CeleryBaseService

__all__ = ['CeleryAnsibleService']


class CeleryAnsibleService(CeleryBaseService):

    def __init__(self):
        super().__init__(name=self.Services.celery_ansible.value, num=10, queue='ansible')

