from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from ops.api.job import JobViewSet


class JobCreateTestCase(SimpleTestCase):
    def test_create_keeps_selected_nodes(self):
        selected_nodes = [object()]
        serializer = Mock(
            validated_data={'nodes': selected_nodes},
            save=Mock(return_value=SimpleNamespace(instant=False)),
        )

        JobViewSet().perform_create(serializer)

        self.assertEqual(serializer.validated_data['nodes'], selected_nodes)
        serializer.save.assert_called_once_with()
