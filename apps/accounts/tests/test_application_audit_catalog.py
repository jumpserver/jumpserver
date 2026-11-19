import importlib.util
import json
from pathlib import Path

from django.test import SimpleTestCase

from accounts.const import AuditEvent, ApplicationCommandEvent, ApplicationEvent


DOCS = Path(__file__).resolve().parents[1] / 'clients' / 'docs'
spec = importlib.util.spec_from_file_location('pam_documentation_build', DOCS / 'build.py')
documentation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(documentation)


class ApplicationAuditCatalogTests(SimpleTestCase):
    def test_catalog_covers_current_audit_types_without_retired_entries(self):
        codes = [item['event'] for item in documentation.AUDIT_EVENTS]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(set(codes), set(AuditEvent.values))
        self.assertNotIn('secret_change_finished', codes)

    def test_related_notifications_are_current_protocol_events(self):
        supported = set(ApplicationEvent.values) | set(ApplicationCommandEvent.values) | {'snapshot'}
        for item in documentation.AUDIT_EVENTS:
            with self.subTest(event=item['event']):
                self.assertLessEqual(set(item['protocol_events']), supported)

    def test_all_locales_document_every_audit_type_with_distinct_meanings(self):
        for locale in documentation.LOCALES:
            texts = json.loads((DOCS / 'translations' / f'{locale}.json').read_text())
            rendered = documentation.audit_event_reference(texts)
            with self.subTest(locale=locale):
                self.assertEqual(set(texts['audit_events']), set(AuditEvent.values))
                for code in AuditEvent.values:
                    entry = texts['audit_events'][code]
                    self.assertTrue(entry['name'])
                    self.assertTrue(entry['meaning'])
                    self.assertIn(f"| {entry['name']} | `{code}` |", rendered)
                    self.assertIn(entry['meaning'], rendered)
