from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from terminal.const import SessionErrorReason
from terminal.models import Session
from terminal.serializers import SessionSerializer


@override_settings(CHANGE_SECRET_AFTER_SESSION_END=False)
class SessionReplayCompletionTests(SimpleTestCase):
    def update_session(self, payload, reason=SessionErrorReason.replay_unsupported,
                       has_replay=False, protocol='ssh'):
        session = Session(protocol=protocol, error_reason=reason, has_replay=has_replay)
        serializer = SessionSerializer(session, data=payload, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch.object(Session, 'save'):
            return serializer.save()

    def test_successful_completion_clears_only_unsupported_placeholder(self):
        for protocol in ('ssh', 'mysql', 'postgresql', 'rdp', 'vnc'):
            with self.subTest(protocol=protocol):
                session = self.update_session(
                    {'has_replay': True, 'replay_size': 355}, protocol=protocol
                )
                self.assertTrue(session.has_replay)
                self.assertEqual(session.replay_size, 355)
                self.assertEqual(session.error_reason, '')

    def test_repeated_completion_clears_unsupported_placeholder(self):
        session = self.update_session({'has_replay': True}, has_replay=True)
        self.assertEqual(session.error_reason, '')

    def test_other_updates_do_not_clear_unsupported(self):
        for payload in ({}, {'has_replay': False}, {'is_finished': True}):
            with self.subTest(payload=payload):
                session = self.update_session(payload)
                self.assertEqual(session.error_reason, SessionErrorReason.replay_unsupported)

    def test_completion_preserves_real_failure(self):
        for reason in (
            SessionErrorReason.connect_failed, SessionErrorReason.replay_create_failed,
            SessionErrorReason.replay_upload_failed, SessionErrorReason.replay_convert_failed,
        ):
            with self.subTest(reason=reason):
                session = self.update_session({'has_replay': True}, reason=reason)
                self.assertEqual(session.error_reason, reason)

    def test_completion_preserves_explicit_error(self):
        reason = SessionErrorReason.replay_upload_failed
        session = self.update_session({'has_replay': True, 'error_reason': reason})
        self.assertEqual(session.error_reason, reason)

    def test_upload_failure_is_recorded(self):
        reason = SessionErrorReason.replay_upload_failed
        session = self.update_session({'error_reason': reason})
        self.assertFalse(session.has_replay)
        self.assertEqual(session.error_reason, reason)
