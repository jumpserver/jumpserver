from rest_framework.generics import ListAPIView
from rest_framework.response import Response

__all__ = ['ReportViewSet']


class ReportViewSet(ListAPIView):
    def list(self, request, *args, **kwargs):
        return Response([])
