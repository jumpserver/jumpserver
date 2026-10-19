from django.test import SimpleTestCase
from django.urls import path
from drf_spectacular.generators import SchemaGenerator
from rest_framework import serializers
from rest_framework.views import APIView

from common.api.generic import JMSGenericViewSet
from common.drf.filters import CustomFilterBackend, IDSpmFilterBackend
from common.drf.metadata import SimpleMetadataWithFilters
from jumpserver.views.schema import CustomAutoSchema
from users.models import User


class SchemaItemSerializer(serializers.Serializer):
    name = serializers.CharField()


class SchemaFilterViewSet(JMSGenericViewSet):
    serializer_class = SchemaItemSerializer
    queryset = User.objects.none()
    authentication_classes = []
    permission_classes = []
    filter_backends = []
    schema = CustomAutoSchema()
    custom_filter_fields = [
        {'name': 'only_mine', 'type': 'boolean', 'methods': ['GET']},
        {'name': 'clone_from', 'schema': {'type': 'string', 'format': 'uuid'}, 'methods': ['POST']},
    ]

    def list(self, request):
        pass

    def create(self, request):
        pass

    def partial_update(self, request, pk=None):
        pass


class SchemaFileView(APIView):
    serializer_class = SchemaItemSerializer
    authentication_classes = []
    permission_classes = []
    filter_backends = [CustomFilterBackend, IDSpmFilterBackend]
    schema = CustomAutoSchema()
    custom_filter_fields = [
        {'name': 'key', 'methods': ['get']},
        {'name': 'expand', 'methods': ['get']},
        {'name': 'key', 'required': True, 'methods': ['delete']},
    ]

    def get(self, request, pk=None):
        pass

    def delete(self, request, pk=None):
        pass


class SchemaFilterTests(SimpleTestCase):
    def setUp(self):
        patterns = [
            path('items/', SchemaFilterViewSet.as_view({'get': 'list', 'post': 'create'})),
            path('items/<uuid:pk>/', SchemaFilterViewSet.as_view({'patch': 'partial_update'})),
            path('files/<uuid:pk>/', SchemaFileView.as_view()),
        ]
        self.schema = SchemaGenerator(patterns=patterns).get_schema(public=True)

    def parameters(self, route, method):
        return {
            p['name']: p for p in self.schema['paths'][route][method].get('parameters', [])
            if p['in'] == 'query'
        }

    def test_list_includes_backends_added_by_project_mixin(self):
        parameters = self.parameters('/items/', 'get')
        self.assertTrue({'spm', 'exclude_spm', 'ids', 'id!', 'label'} <= parameters.keys())
        self.assertEqual(parameters['only_mine']['schema']['type'], 'boolean')
        self.assertNotIn('clone_from', parameters)

    def test_write_parameters_do_not_include_queryset_filters(self):
        parameters = self.parameters('/items/', 'post')
        self.assertEqual(set(parameters), {'clone_from'})
        self.assertEqual(parameters['clone_from']['schema']['format'], 'uuid')
        self.assertEqual(self.parameters('/items/{id}/', 'patch'), {})

    def test_apiview_parameters_are_scoped_to_each_method(self):
        get = self.parameters('/files/{id}/', 'get')
        delete = self.parameters('/files/{id}/', 'delete')
        self.assertEqual(set(get), {'key', 'expand'})
        self.assertFalse(get['key']['required'])
        self.assertEqual(set(delete), {'key'})
        self.assertTrue(delete['key']['required'])
        self.assertNotIn('methods', delete['key'])
        self.assertEqual(SchemaFileView.custom_filter_fields[2]['methods'], ['delete'])

    def test_legacy_field_declarations_keep_their_types_and_locations(self):
        view = SchemaFileView()
        view.custom_filter_fields = [
            'plain',
            {'name': 'enabled', 'type': 'boolean'},
            {'name': 'X-Example', 'location': 'header', 'required': True},
        ]
        parameters = CustomFilterBackend().get_schema_operation_parameters(view)
        self.assertEqual(parameters[0]['schema'], {'type': 'string'})
        self.assertEqual(parameters[1]['schema'], {'type': 'boolean'})
        self.assertEqual(parameters[2]['in'], 'header')
        self.assertTrue(parameters[2]['required'])

    def test_parameter_dictionaries_are_also_usable_by_options_metadata(self):
        view = SchemaFileView()
        fields = SimpleMetadataWithFilters.get_filters_fields(view)
        self.assertEqual(fields, ['key', 'expand'])
        self.assertEqual(len(view.custom_filter_fields), 3)
