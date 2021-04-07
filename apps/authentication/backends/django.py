from django.contrib.auth import backends
from .mixins import ModelBackendMixin


class ModelBackend(ModelBackendMixin, backends.ModelBackend):
    pass
