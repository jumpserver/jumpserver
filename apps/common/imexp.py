# -*- coding: utf-8 -*-
#
import codecs
import csv
import uuid
import json
from io import StringIO
import warnings
import chardet

from django import forms
from django.utils import timezone
from django.views import View
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, FieldDoesNotExist
from django.utils.encoding import force_text
from django.http import Http404, HttpResponseRedirect, HttpResponse, JsonResponse


class ModelExportPostMixin:
    """
    将用户post上来的数据转存到cache, 生成一个uuid, redirect 到GET URL
    """
    redirect_url = None
    error_message = 'Json object not valid'
    keyword = 'spm'
    cache_key = None
    request = None

    def get_redirect_url(self):
        if self.redirect_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.redirect_url)
        else:
            msg = "No URL to redirect to. Provide a redirect_url."
            raise ImproperlyConfigured(msg)
        sep = "?" if url.find('?') else '&'
        url = '{}{}{}={}'.format(url, sep, self.keyword, self.cache_key)
        return url

    def save_objects_id_to_cache(self, objects_id):
        self.cache_key = uuid.uuid4().hex
        cache.set(self.cache_key, objects_id, 300)
        return self.cache_key

    def get_objects_id_from_request(self):
        try:
            objects_id = json.loads(self.request.body)
        except ValueError:
            raise Http404(self.error_message)
        return objects_id

    def get_redirect_response(self):
        objects_id = self.get_objects_id_from_request()
        self.save_objects_id_to_cache(objects_id)
        url = self.get_redirect_url()
        return HttpResponseRedirect(redirect_to=url)

    # View need implement it
    # def post(self, request, *args, **kwargs):
    #     self.request = request
    #     return self.get_redirect_response()


class MethodField:
    def __init__(self, name, verbose_name=None):
        self.name = name
        self.verbose_name = verbose_name

        if self.verbose_name is None:
            self.verbose_name = name


class FieldCheckMeta(type):

    def __new__(cls, name, bases, attrs):
        error = cls.validate_fields(attrs)
        if not error:
            return super().__new__(cls, name, bases, attrs)
        else:
            raise AttributeError(error)

    @staticmethod
    def validate_fields(attrs):
        model = attrs.get('model')
        fields = attrs.get('fields')
        if model is None or fields in ('__all__', None):
            return None

        all_attr = [attr for attr in dir(model) if not attr.startswith('_')]
        invalid_fields = []

        for field in fields:
            if field not in all_attr:
                invalid_fields.append(field)

        if not invalid_fields:
            return None

        error = 'model {} is not have `{}` attr, check `fields` setting'.format(
            model._meta.model_name, ', '.join(invalid_fields)
        )
        return error


class ModelFieldsMixin(metaclass=FieldCheckMeta):
    model = None
    fields = None
    exclude = None
    errors = None
    __cleaned_fields_name = None
    __is_valid = False
    __defined_fields_name = None

    def get_define_fields_name(self):
        """
        Calculate fields, fields may be `__all__`, `(field1, field2)` or
        set `exclude` so do that
        :return: => list
        """
        if self.__defined_fields_name:
            return self.__defined_fields_name

        all_fields = [field.name for field in self.model._meta.fields]
        if self.fields == '__all__':
            return all_fields
        elif self.fields:
            return self.fields
        elif self.exclude:
            return list(set(all_fields) - set(self.exclude))
        else:
            return []

    def get_field(self, field_name):
        try:
            return self.model._meta.get_field(field_name)
        except FieldDoesNotExist:
            attr = getattr(self.model, field_name)
            if hasattr(attr, 'verbose_name'):
                verbose_name = getattr(attr, 'verbose_name')
            else:
                verbose_name = field_name
            return MethodField(field_name, verbose_name)

    def get_fields(self, cleaned_fields_name):
        """
        Get fields by fields name
        :param cleaned_fields_name:
        :return:
        """
        fields = []
        for name in cleaned_fields_name:
            fields.append(self.get_field(name))
        return fields

    def get_define_fields(self):
        fields_name = self.get_define_fields_name()
        return self.get_fields(fields_name)

    def valid_field_name(self, field_name):
        if not hasattr(self.model, field_name):
            msg = "{} not has `{}` attr".format(self.model._meta.model_name, field_name)
            raise AttributeError(msg)
        elif field_name not in self.get_define_fields_name():
            msg = '{} not allowed by server'.format(field_name)
            raise AttributeError(msg)

    def is_valid(self, fields, ignore_exception=True):
        self.__cleaned_fields_name = []
        self.errors = {}

        for field_name in fields:
            try:
                self.valid_field_name(field_name)
                self.__cleaned_fields_name.append(field_name)
            except AttributeError as e:
                if not ignore_exception:
                    self.errors[field_name] = str(e)

        if self.errors:
            self.__is_valid = False
            return False
        else:
            self.__is_valid = True
            return True

    @property
    def field_verbose_name_mapping(self):
        mapping = {}
        for field in self.get_define_fields():
            mapping[field.verbose_name] = field.name
        return mapping

    @property
    def cleaned_fields(self):
        if self.__cleaned_fields_name is None:
            raise AttributeError("Run `is_valid` first")

        if not self.__is_valid:
            warnings.warn("Is not valid, result may be not complete")

        return self.get_fields(self.__cleaned_fields_name)


class ModelExportGetMixin(ModelFieldsMixin):
    filename_prefix = 'jumpserver'
    response = None
    writer = None
    model = None
    objects_id = None
    queryset = None
    keyword = 'spm'

    def get_filename(self):
        now = timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')
        filename = '{}-{}-{}.csv'.format(
            self.filename_prefix, self.model._meta.model_name, now
        )
        return filename

    def get_objects_id(self):
        cache_key = self.request.GET.get(self.keyword)
        self.objects_id = cache.get(cache_key, [])
        return self.objects_id

    def get_queryset(self):
        queryset = None

        if self.queryset:
            queryset = self.queryset
        elif self.queryset is None:
            queryset = self.model._meta.default_manager.all()

        if queryset is None:
            raise AttributeError("Get queryset failed, set `queryset` or `model`")

        objects_id = self.get_objects_id()
        queryset_filtered = queryset.filter(id__in=objects_id)
        return queryset_filtered

    def initial_csv_response(self):
        filename = self.get_filename()
        self.response = HttpResponse(content_type='text/csv')
        self.response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        self.response.write(codecs.BOM_UTF8)
        self.writer = csv.writer(self.response, dialect='excel', quoting=csv.QUOTE_MINIMAL)
        header = []
        for field in self.get_define_fields():
            if hasattr(field, 'verbose_name'):
                header.append(getattr(field, 'verbose_name'))
            else:
                header.append(getattr(field, 'name'))
        self.writer.writerow(header)

    def make_csv_response(self):
        self.initial_csv_response()
        queryset = self.get_queryset()

        for instance in queryset:
            data = [getattr(instance, field.name) for field in self.get_define_fields()]
            self.writer.writerow(data)
        return self.response


class FileForm(forms.Form):
    file = forms.FileField()


class ModelImportPostMixin(ModelFieldsMixin):
    form_context = "file"
    csv_data = None
    form_class = FileForm
    stream = None

    def get_form(self):
        form = self.form_class(self.request.POST)
        if form.is_valid():
            raise Http404("Form is not valid")
        return form

    def get_stream(self):
        self.stream = self.get_form().cleaned_data[self.form_context]
        return self.stream

    def get_csv_data(self, stream=None):
        if stream is None:
            stream = self.stream
        result = chardet.detect(stream.read())
        stream.seek(0)
        raw_data = stream.read().decode(result['encoding'])\
            .strip(codecs.BOM_UTF8.decode())
        csv_file = StringIO(raw_data)
        reader = csv.reader(csv_file)
        csv_data = [row for row in reader]
        self.csv_data = csv_data
        return csv_data

    def cleaned_post_fields(self):
        fields = []
        header = self.csv_data[0]
        fields_name = [self.field_verbose_name_mapping.get(v) for v in header]
        for name in fields_name:
            if name in self.get_define_fields():
                fields.append(self.get_field(name))
            else:
                fields.append(None)
        return fields

    def create_or_update(self):
        stream = self.get_stream()
        csv_data = self.get_csv_data(stream)
        cleaned_fields = self.cleaned_post_fields()



class ModelImportView(ModelImportPostMixin):
    def post(self, request, *args, **kwargs):
        return self.create_or_update()


class ModelExportView(ModelExportPostMixin, ModelExportGetMixin, View):
    model = None
    filename_prefix = 'jumpserver'

    def post(self, request, *args, **kwargs):
        return self.get_redirect_response()

    def get(self, request, *args, **kwargs):
        self.request = request
        response = self.make_csv_response()
        return response
