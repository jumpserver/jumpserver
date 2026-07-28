from django.test import TestCase

from users.models import User

from common.drf.filters import LookupFilterBackend


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
