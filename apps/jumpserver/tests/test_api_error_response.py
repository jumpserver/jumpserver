from unittest.mock import patch

from django.db import transaction
from django.test import SimpleTestCase, override_settings
from django.urls import path
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from jumpserver.views.error_views import handler500


class BrokenAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def get(self, request):
        raise RuntimeError('test traceback marker')

    post = get


class InvalidAPIView(BrokenAPIView):
    def get(self, request):
        raise ValidationError({'name': ['Required']})


urlpatterns = [
    path('broken/', transaction.non_atomic_requests(BrokenAPIView.as_view()), name='index'),
    path('invalid/', transaction.non_atomic_requests(InvalidAPIView.as_view())),
]


@override_settings(
    ROOT_URLCONF=__name__, MIDDLEWARE=[], ALLOWED_HOSTS=['testserver'], DEBUG_DEV=False,
)
class ApiErrorResponseTests(SimpleTestCase):
    def setUp(self):
        self.client.raise_request_exception = False

    def test_json_error_is_brief_with_debug_on_or_off(self):
        for debug in (True, False):
            with self.subTest(debug=debug), self.settings(DEBUG=debug):
                with patch('common.drf.exc_handlers.unexpected_exception_logger.exception') as log:
                    response = self.client.get('/broken/', HTTP_ACCEPT='application/json')
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.json(), {'code': 'internal_error', 'detail': 'Server internal error'})
                self.assertNotIn(b'test traceback marker', response.content)
                log.assert_called_once()

    @override_settings(DEBUG=True)
    def test_browser_navigation_keeps_html_traceback(self):
        response = self.client.get(
            '/broken/', HTTP_ACCEPT='text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn('text/html', response['Content-Type'])
        self.assertTrue(b'test traceback marker' in response.content)
        self.assertTrue(b'Traceback' in response.content)

    @override_settings(DEBUG=True)
    def test_accept_quality_controls_error_format_even_with_json_body(self):
        for accept, expected in (
            ('application/json,text/html;q=0.5', 'application/json'),
            ('text/html,application/json;q=0.5', 'text/html'),
        ):
            with self.subTest(accept=accept):
                response = self.client.post('/broken/', {}, content_type='application/json', HTTP_ACCEPT=accept)
                self.assertEqual(response.status_code, 500)
                self.assertIn(expected, response['Content-Type'])

    def test_validation_error_is_unchanged(self):
        response = self.client.get('/invalid/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'name': ['Required']})

    def test_production_handler_uses_accept_for_get_requests(self):
        from django.test import RequestFactory

        response = handler500(RequestFactory().get('/broken/', HTTP_ACCEPT='application/json'))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response['Content-Type'], 'application/json')
