from django.test import TestCase
from users.models import User

# Create your tests here.

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


class LookupFilterBackendTests(TestCase):
    def setUp(self):
        self.backend = LookupFilterBackend()

    def test_is_text_lookup_field_for_text_fields(self):
        self.assertTrue(self.backend.is_text_lookup_field(User, "username"))
        self.assertTrue(self.backend.is_text_lookup_field(User, "name"))

    def test_is_text_lookup_field_for_non_text_fields(self):
        self.assertFalse(self.backend.is_text_lookup_field(User, "id"))

    def test_is_text_lookup_field_for_related_field(self):
        self.assertTrue(self.backend.is_text_lookup_field(User, "groups__name"))
        self.assertFalse(self.backend.is_text_lookup_field(User, "groups__id"))

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
