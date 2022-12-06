from rest_framework_bulk import BulkModelViewSet

from common.mixins import CommonApiMixin

__all__ = ['SelfBulkModelViewSet']


class SelfBulkModelViewSet(CommonApiMixin, BulkModelViewSet):

    def get_queryset(self):
        if hasattr(self, 'model'):
            return self.model.objects.filter(creator=self.request.user)
        else:
            assert self.queryset is None, (
                    "'%s' should not include a `queryset` attribute"
                    % self.__class__.__name__
            )
