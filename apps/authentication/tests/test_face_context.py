from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.exceptions import NotFound

from authentication.api.face import FaceContextApi
from authentication.const import FACE_SESSION_KEY


class FaceContextApiTest(SimpleTestCase):
    @patch("authentication.api.face.cache")
    def test_status_rejects_token_from_an_older_capture(self, cache):
        view = FaceContextApi()
        view.request = SimpleNamespace(
            session={FACE_SESSION_KEY: "n" * 32},
            query_params={"token": "o" * 32},
        )

        with self.assertRaises(NotFound):
            view.get(None)

        cache.get.assert_not_called()

    @patch("authentication.api.face.cache")
    def test_status_reads_the_requested_current_token(self, cache):
        token = "c" * 32
        cache.get.return_value = {
            "is_finished": True,
            "success": False,
            "error_message": "Timed out",
        }
        view = FaceContextApi()
        view.request = SimpleNamespace(
            session={FACE_SESSION_KEY: token},
            query_params={"token": token},
        )

        response = view.get(None)

        cache.get.assert_called_once_with(view.get_face_cache_key(token))
        self.assertEqual(
            response.data,
            {
                "is_finished": True,
                "success": False,
                "error_message": "Timed out",
            },
        )
