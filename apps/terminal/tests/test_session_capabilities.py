from django.test import SimpleTestCase

from terminal.models import Session, Terminal
from terminal.serializers import SessionSerializer


class DatabaseWorkbenchSessionTests(SimpleTestCase):
    def test_mysql_workbench_and_cli_capabilities(self):
        terminal = Terminal(type='koko')
        for session_type, can_join in (('normal', True), ('db_workbench', False)):
            with self.subTest(session_type=session_type):
                serializer = SessionSerializer(data={'type': session_type}, partial=True)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                session = Session(
                    terminal=terminal, protocol='mysql', login_from='WT',
                    has_replay=True, **serializer.validated_data,
                )
                self.assertEqual(session.type, session_type)
                self.assertEqual(session.can_join, can_join)
                self.assertTrue(session.can_terminate)
                self.assertTrue(session.can_replay())
