from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.exceptions import NotFound

from authentication.api.face import FaceContextApi
from authentication.api.connection_token import ConnectionTokenViewSet
from authentication.const import FACE_SESSION_KEY
from authentication.mixins import AuthFaceMixin


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


class FaceContextCreationTest(SimpleTestCase):
    @patch("authentication.mixins.cache")
    def test_connection_token_uses_authenticated_user_without_login_mixin(self, cache):
        view = ConnectionTokenViewSet()
        view.request = SimpleNamespace(
            user=SimpleNamespace(id="asset-user", is_face_code_set=True),
            session={},
        )
        response = SimpleNamespace(data={"id": "connection-id"})

        view.create_face_verify(response)

        token = response.data["face_token"]
        self.assertEqual(view.request.session[FACE_SESSION_KEY], token)
        context = cache.set.call_args.args[1]
        self.assertEqual(context["user_id"], "asset-user")
        self.assertEqual(context["action"], "login_asset")
        self.assertEqual(context["connection_token_id"], "connection-id")

    @patch("authentication.mixins.cache")
    def test_login_context_still_uses_session_user(self, cache):
        view = AuthFaceMixin()
        view.request = SimpleNamespace(user=SimpleNamespace(id="request-user"), session={})
        view.get_user_from_session = lambda: SimpleNamespace(id="session-user")

        view.create_face_verify_context()

        self.assertEqual(cache.set.call_args.args[1]["user_id"], "session-user")
