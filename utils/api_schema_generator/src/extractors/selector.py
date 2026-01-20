from django.views.generic.edit import FormView as DjangoFormView
from django.views import View as DjangoView
from rest_framework.views import APIView as DrfAPIView

from routing.resolver import View

from .django_func_view import DjangoFunctionViewExtractor
from .django_form_view import DjangoFormViewExtractor
from .django_view import DjangoViewExtractor
from .drf_api_view import DrfAPIViewExtractor


def select_extractor(view: View):

    if view.is_func_based:
        return DjangoFunctionViewExtractor(view)

    view_class = view.view_class

    if issubclass(view_class, DrfAPIView):
        return DrfAPIViewExtractor(view)

    if issubclass(view_class, DjangoFormView):
        return DjangoFormViewExtractor(view)

    if issubclass(view_class, DjangoView):
        return DjangoViewExtractor(view)

    raise NotImplementedError(f'Unsupported view class: {view_class}')
    