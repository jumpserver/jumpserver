from django.utils.functional import LazyObject


class LabeledResourceType(LazyObject):
    @staticmethod
    def get_res_types():
        from rbac.models import ContentType
        from .mixins import LabeledMixin
        content_types = ContentType.objects.all()
        ids = []
        for ct in content_types:
            model_cls = ct.model_class()
            if not model_cls:
                continue
            if model_cls._meta.parents:
                continue
            if issubclass(model_cls, LabeledMixin):
                ids.append(ct.id)
        return ContentType.objects.filter(id__in=ids)

    def _setup(self):
        self._wrapped = self.get_res_types()


label_resource_types = LabeledResourceType()
