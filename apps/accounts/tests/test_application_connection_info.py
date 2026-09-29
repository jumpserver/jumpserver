from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from accounts.api.account.application import IntegrationApplicationViewSet


class ApplicationConnectionInfoTests(SimpleTestCase):
    def test_secret_response_includes_the_application_org_and_sdk_endpoint(self):
        application = SimpleNamespace(id=uuid4(), org_id=uuid4(), secret='test-only-secret')
        request = APIRequestFactory().get('/api/v1/accounts/integration-applications/example/secret/')
        # Root-org administrators can view applications belonging to another org.
        request.org_id = uuid4()
        view = IntegrationApplicationViewSet()
        view.get_object = Mock(return_value=application)
        response = view.get_once_secret(request)

        self.assertEqual(response.data, {
            'id': application.id,
            'secret': application.secret,
            'org_id': str(application.org_id),
            'endpoint': 'http://testserver',
        })
        self.assertEqual(response['Cache-Control'], 'no-store')
