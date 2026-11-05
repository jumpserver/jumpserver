from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from ops.serializers.job import JobExecutionSerializer, JobSerializer
from common.serializers.fields import LabeledChoiceField
from jumpserver.views.schema import LabeledChoiceFieldExtension


class JobParametersTests(SimpleTestCase):
    def test_parameters_keep_native_json_types(self):
        values = {'gpus': 4, 'enabled': True, 'hosts': ['server-1'], 'options': {'mode': 'read'}}
        for serializer in [JobSerializer(), JobExecutionSerializer()]:
            self.assertEqual(serializer.fields['parameters'].run_validation(values), values)
        self.assertEqual(JobExecutionSerializer().validate_parameters(values),
                         {f'jms_{key}': value for key, value in values.items()})

    def test_non_object_parameters_are_rejected_before_job_creation(self):
        for serializer in [JobSerializer(), JobExecutionSerializer()]:
            for value in ['{}', '[1]', [], 1, True]:
                with self.assertRaises(ValidationError):
                    serializer.fields['parameters'].run_validation(value)

    def test_omitted_parameters_default_to_an_empty_object(self):
        for serializer in [JobSerializer(), JobExecutionSerializer()]:
            self.assertEqual(serializer.fields['parameters'].get_default(), {})

    def test_choice_schema_keeps_allowed_values_and_native_types(self):
        for choices, expected_type in [([('skip', 'Skip'), ('privileged_only', 'Privileged only')], 'string'),
                                      ([(0, 'Disabled'), (1, 'Enabled')], 'integer')]:
            field = LabeledChoiceField(choices=choices)
            schema = LabeledChoiceFieldExtension(field).map_serializer_field(None, 'request')
            self.assertEqual(schema['properties']['value']['type'], expected_type)
            self.assertEqual(schema['properties']['value']['enum'], [value for value, _ in choices])
