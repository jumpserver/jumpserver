#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~
#

from django.core.paginator import InvalidPage, Paginator


class View(object):

    http_method_names = []

    def __init__(self, **kwargs):
        pass

    @classmethod
    def as_view(cls, **initkwargs):
        pass

    def dispatch(self, request, *args, **kwargs):
        pass

    def http_method_not_allowed(self, request, *args, **kwargs):
        pass

    def options(self, request, *args, **kwargs):
        pass

    def _allowed_method(self):
        pass


class TemplateResponseMixin(object):
    template_name = None
    template_engine = None
    response_class = None
    content_type = None

    def render_to_response(self, context, **response_kwargs):
        pass

    def get_template_name(self):
        pass


class ContextMixin(object):
    def get_context_data(self, **kwargs):
        pass


class RedirectView(View):
    permanent = False
    url = None
    pattern_name = None
    query_string = False

    def get_redirect_url(self, *args, **kwargs):
        pass

    def get(self, request, *args, **kwargs):
        pass

    def head(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass

    def options(self, request, *args, **kwargs):
        pass

    def delete(self, request, *args, **kwargs):
        pass

    def put(self, request, *args, **kwargs):
        pass

    def patch(self, request, *args, **kwargs):
        pass


class TemplateView(TemplateResponseMixin, ContextMixin, View):
    def get(self, request, *args, **kwargs):
        pass


class SingleObjectMixin(ContextMixin):
    model = None
    queryset = None
    slug_field = 'slug'
    context_object_name = None
    slug_url_kwarg = 'slug'
    pk_url_kwarg = 'pk'
    query_pk_and_slug = False

    def get_object(self):
        pass

    def get_queryset(self):
        pass

    def get_slug_field(self):
        pass

    def get_context_object_name(self, obj):
        pass

    def get_context_data(self, **kwargs):
        pass


class BaseDetailView(SingleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        pass


class SingleObjectTemplateResponseMixin(TemplateResponseMixin):
    template_name_field = None
    template_name_suffix = '_detail'

    def get_template_name(self):
        pass


class DetailView(SingleObjectTemplateResponseMixin, BaseDetailView):
    pass


class FormMixin(ContextMixin):
    initial = {}
    form_class = None
    success_url = None
    prefix = None

    def get_initial(self):
        pass

    def get_prefix(self):
        pass

    def get_form_class(self):
        pass

    def get_form(self, form_class):
        pass

    def get_form_kwargs(self):
        pass

    def get_success_url(self):
        pass

    def form_valid(self, form):
        pass

    def form_invalid(self, form):
        pass

    def get_context_data(self, **kwargs):
        pass


class ModelFormMixin(FormMixin, SingleObjectMixin):
    fields = None

    def get_form_class(self):
        pass

    def get_form_kwargs(self):
        pass

    def get_success_url(self):
        pass

    def form_valid(self, form):
        pass


class ProcessFormView(View):
    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass

    def put(self, request, *args, **kwargs):
        pass


class BaseFormView(FormMixin, ProcessFormView):
    pass


class FormView(TemplateResponseMixin, BaseFormView):
    pass


class BaseCreateView(ModelFormMixin, ProcessFormView):
    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass


class CreateView(SingleObjectTemplateResponseMixin, BaseCreateView):
    template_name_suffix = '_form'


class BaseUpdateView(ModelFormMixin, ProcessFormView):
    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass


class UpdateView(SingleObjectTemplateResponseMixin, BaseUpdateView):
    template_name_suffix = '_form'


class DeletionMixin(object):
    success_url = None

    def delete(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass

    def get_success_url(self):
        pass


class BaseDeleteView(DeletionMixin, BaseDetailView):
    pass


class DeleteView(SingleObjectTemplateResponseMixin, BaseDeleteView):
    pass


class MultipleObjectMixin(ContextMixin):
    allow_empty = True
    queryset = None
    model = None
    paginate_by = None
    paginate_orphans = 0
    context_object_name = None
    paginator_class = Paginator
    page_kwarg = 'page'
    ordering = None

    def get_queryset(self):
        pass

    def get_ordering(self):
        pass

    def paginate_queryset(self, queryset, page_size):
        pass

    def get_paginate_by(self, queryset):
        pass

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        pass

    def get_paginate_orphans(self):
        pass

    def get_allow_empty(self):
        pass

    def get_context_object_name(self, object_list):
        pass

    def get_context_data(self, **kwargs):
        pass


class BaseListView(MultipleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        pass


class MultipleObjectTemplateResponseMixin(TemplateResponseMixin):
    template_name_suffix = '_list'

    def get_template_name(self):
        pass


class ListView(MultipleObjectTemplateResponseMixin, BaseListView):
    pass
