from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase
from requests import ConnectionError
from rest_framework.test import APIRequestFactory, force_authenticate

from users.models import User

# Create your tests here.

from common.api.jdmc import JdmcSSOTokenAPI
from common.drf.filters import LookupFilterBackend
from .utils import random_string, signer


def test_signer_len():
    results = {}
    for i in range(1, 4096):
        s = random_string(i)
        encs = signer.sign(s)
        results[i] = (len(encs)/len(s))
    results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    print(results)


class DummySearchView:
    search_fields = ["username", "=name", "groups__name"]
    filterset_fields = ["email", "groups__id", "groups__name"]


class DummyFiltersetDictView:
    filterset_fields = {
        "username": ["exact"],
        "email": ["icontains"],
    }


class LookupFilterBackendTests(TestCase):
    def setUp(self):
        self.backend = LookupFilterBackend()
        self.view = DummySearchView()

    def test_is_text_lookup_field_for_text_fields(self):
        self.assertTrue(self.backend.is_text_lookup_field(User, "username"))
        self.assertTrue(self.backend.is_text_lookup_field(User, "name"))

    def test_is_text_lookup_field_for_non_text_fields(self):
        self.assertFalse(self.backend.is_text_lookup_field(User, "id"))

    def test_is_text_lookup_field_for_related_field(self):
        self.assertTrue(self.backend.is_text_lookup_field(User, "groups__name"))
        self.assertFalse(self.backend.is_text_lookup_field(User, "groups__id"))

    def test_is_allowed_filterset_field_uses_only_filterset_fields(self):
        self.assertFalse(self.backend.is_allowed_filterset_field(self.view, "username"))
        self.assertFalse(self.backend.is_allowed_filterset_field(self.view, "name"))
        self.assertTrue(self.backend.is_allowed_filterset_field(self.view, "groups__name"))
        self.assertTrue(self.backend.is_allowed_filterset_field(self.view, "email"))
        self.assertFalse(self.backend.is_allowed_filterset_field(self.view, "password"))

    def test_get_allowed_filterset_fields_from_dict(self):
        self.assertEqual(
            self.backend.get_allowed_filterset_fields(DummyFiltersetDictView()),
            {"username", "email"}
        )

    def test_supported_dynamic_text_lookups(self):
        self.assertEqual(
            self.backend.dynamic_text_lookups,
            {"icontains", "startswith"}
        )

    def test_supported_dynamic_value_lookups(self):
        self.assertEqual(
            self.backend.dynamic_value_lookups,
            {"in"}
        )

    def test_supported_negated_text_lookups(self):
        self.assertEqual(
            self.backend.negated_text_lookups,
            {"icontains", "startswith"}
        )

    def test_supported_negated_value_lookups(self):
        self.assertEqual(
            self.backend.negated_value_lookups,
            {"exact", "in"}
        )

    def test_is_value_lookup_field(self):
        self.assertTrue(self.backend.is_value_lookup_field(User, "username"))
        self.assertTrue(self.backend.is_value_lookup_field(User, "id"))
        self.assertFalse(self.backend.is_value_lookup_field(User, "groups"))

    def test_split_lookup_param(self):
        self.assertEqual(
            self.backend.split_lookup_param("username"),
            ("username", "exact")
        )
        self.assertEqual(
            self.backend.split_lookup_param("username__icontains"),
            ("username", "icontains")
        )

    def test_split_csv_values(self):
        self.assertEqual(
            self.backend.split_csv_values(["alice, bob", "carol"]),
            ["alice", "bob", "carol"]
        )

    def test_normalize_search_field(self):
        self.assertEqual(self.backend.normalize_search_field("^username"), "username")
        self.assertEqual(self.backend.normalize_search_field("=name"), "name")
        self.assertEqual(self.backend.normalize_search_field("groups__name"), "groups__name")

    def test_search_filter_split_search_groups(self):
        from common.drf.filters import SearchFilter

        self.assertEqual(
            SearchFilter.split_search_groups("alice,bob"),
            [["alice"], ["bob"]]
        )
        self.assertEqual(
            SearchFilter.split_search_groups("alice admin,bob"),
            [["alice", "admin"], ["bob"]]
        )


class JdmcSSOTokenAPITests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = JdmcSSOTokenAPI.as_view()

    @staticmethod
    def user(username='admin', has_jdmc=True):
        return SimpleNamespace(
            pk=username,
            username=username,
            is_authenticated=True,
            is_valid=True,
            has_jdmc=has_jdmc,
        )

    def get(self, user=None):
        request = self.factory.get('/api/v1/common/jdmc/sso-token/')
        force_authenticate(request, user=user or self.user())
        return self.view(request)

    @patch('common.api.jdmc.request_jdmc')
    def test_admin_can_request_kotl_token(self, request_jdmc):
        upstream = Mock(status_code=200, text='')
        upstream.json.return_value = {
            'code': 0,
            'data': {'token': 'kotl_token'},
        }
        request_jdmc.return_value = upstream

        response = self.get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'token': 'kotl_token'})
        request_jdmc.assert_called_once_with(
            method='POST',
            path='/jdmc/api/v1/auth/tokens',
            json={'name': 'admin'},
        )

    @patch('common.api.jdmc.request_jdmc')
    def test_upstream_connection_error_returns_bad_gateway(self, request_jdmc):
        request_jdmc.side_effect = ConnectionError('socket unavailable')

        response = self.get()

        self.assertEqual(response.status_code, 502)
        self.assertIn('socket unavailable', response.data['error'])

    @patch('common.api.jdmc.request_jdmc')
    def test_missing_token_returns_bad_gateway(self, request_jdmc):
        upstream = Mock(status_code=200, text='')
        upstream.json.return_value = {'code': 0, 'data': {}}
        request_jdmc.return_value = upstream

        response = self.get()

        self.assertEqual(response.status_code, 502)

    def test_user_without_jdmc_permission_is_forbidden(self):
        response = self.get(self.user(username='other', has_jdmc=False))

        self.assertEqual(response.status_code, 403)
