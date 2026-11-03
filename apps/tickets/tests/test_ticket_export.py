from django.test import SimpleTestCase
from django.utils.translation import override

from tickets.serializers.ticket.ticket import TicketProcessMapField, TicketRequestItemsField, TicketSnapshotField


class TicketExportTests(SimpleTestCase):
    @override('en')
    def test_process_export_supports_custom_nodes_and_new_states(self):
        rows = [
            {'name': 'Production owner', 'approval_level': 6, 'state': 'approved',
             'assignees_display': ['Alice', 'Bob'], 'processor_display': 'Alice',
             'approval_date': '2026-10-16T10:00:00Z'},
            {'approval_level': 7, 'state': 'cancelled', 'approval_date': ''},
        ]
        result = TicketProcessMapField().to_file_representation(rows)
        self.assertIn('Production owner', result)
        self.assertIn('Alice, Bob', result)
        self.assertIn('7', result)
        self.assertIn('Cancelled', result)
        self.assertNotIn("'assignees_display'", result)

    def test_request_export_uses_readable_plugin_items_and_keeps_zero(self):
        result = TicketRequestItemsField().to_file_representation([
            {'label': 'Assets', 'value': ['Host A', 'Host B']},
            {'label': 'Duration', 'value': 0},
            {'label': 'Reminder', 'value': None},
        ])
        self.assertEqual(result, 'Assets: Host A, Host B\nDuration: 0\nReminder: -')
        self.assertEqual(TicketRequestItemsField().to_file_representation([]), '-')
        self.assertNotIn('secret', TicketSnapshotField().to_file_representation({'secret': 'hidden'}))
