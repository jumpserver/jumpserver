import hashlib
import json
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate

from common.storage.replay import SessionPartReplayStorageHandler
from terminal.api.session.session import SessionReplayViewSet


class SessionReplayIndexStorageTests(SimpleTestCase):
    def setUp(self):
        self.session = SimpleNamespace(id=uuid.uuid4(), asset_id=uuid.uuid4())
        self.storage = SessionPartReplayStorageHandler(self.session)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def make_files(self, *, indexed=True, tampered=False, schema=None):
        document = {
            'schema': self.storage.INDEX_SCHEMA,
            'version': 1,
            'session': {'id': str(self.session.id)},
            'source': {'part_count': 1, 'duration_ms': 1200},
            'event_count': 1,
            'events': [{'ordinal': 0, 'kind': 'screen_text', 'replay_ms': 800,
                        'ocr': {'text': 'example', 'delta_text': 'example'}}],
        }
        if schema is not None:
            document['schema'] = schema
        index_bytes = json.dumps(document).encode('utf-8')
        index_name = '{}.index.v1.json'.format(self.session.id)
        index_path = self.root / index_name
        index_path.write_bytes(index_bytes + (b' ' if tampered else b''))
        manifest = {
            'type': 'mp4',
            'files': [{'name': '{}.0.part.mp4'.format(self.session.id), 'size': 100}],
        }
        if indexed:
            manifest['index'] = {
                'schema': self.storage.INDEX_SCHEMA,
                'schema_version': 1,
                'name': index_name,
                'media_type': self.storage.INDEX_MEDIA_TYPE,
                'size': len(index_bytes),
                'sha256': hashlib.sha256(index_bytes).hexdigest(),
            }
        manifest_name = '{}.replay.json'.format(self.session.id)
        (self.root / manifest_name).write_text(json.dumps(manifest))
        return manifest_name, index_path, index_bytes

    def read(self, manifest_name, index_path):
        with (
                patch('common.storage.replay.default_storage',
                      SimpleNamespace(base_location=str(self.root))),
                patch.object(self.storage, 'get_part_file_path_url',
                             return_value=(manifest_name, '')),
                patch.object(self.storage, '_get_verified_index_path',
                             return_value=str(index_path)) as verified,
        ):
            result = self.storage.get_verified_index_bytes()
        return result, verified

    def test_returns_exact_verified_sidecar_bytes(self):
        manifest_name, index_path, expected = self.make_files()

        actual, verified = self.read(manifest_name, index_path)

        self.assertEqual(actual, expected)
        verified.assert_called_once()

    def test_missing_index_descriptor_is_not_found(self):
        manifest_name, index_path, _ = self.make_files(indexed=False)

        with self.assertRaises(FileNotFoundError):
            self.read(manifest_name, index_path)

    def test_missing_replay_manifest_is_not_found(self):
        with patch.object(self.storage, 'get_part_file_path_url',
                          return_value=(None, 'replay manifest not found')):
            with self.assertRaises(FileNotFoundError):
                self.storage.get_verified_index_bytes()

    def test_invalid_index_descriptor_is_not_treated_as_absent(self):
        manifest_name, index_path, _ = self.make_files()
        manifest_path = self.root / manifest_name
        manifest = json.loads(manifest_path.read_text())
        manifest['index'] = None
        manifest_path.write_text(json.dumps(manifest))

        with self.assertRaises(ValueError):
            self.read(manifest_name, index_path)

    def test_missing_declared_sidecar_is_invalid_bundle(self):
        manifest_name, _, _ = self.make_files()
        with (
                patch('common.storage.replay.default_storage',
                      SimpleNamespace(base_location=str(self.root))),
                patch.object(self.storage, 'get_part_file_path_url',
                             return_value=(manifest_name, '')),
                patch.object(self.storage, '_get_verified_index_path',
                             side_effect=FileNotFoundError('missing sidecar')),
        ):
            with self.assertRaisesRegex(ValueError, 'declared replay index file is missing'):
                self.storage.get_verified_index_bytes()

    def test_tampered_sidecar_is_rejected(self):
        manifest_name, index_path, _ = self.make_files(tampered=True)

        with self.assertRaises(ValueError):
            self.read(manifest_name, index_path)

    def test_verified_but_unsupported_document_is_rejected(self):
        manifest_name, index_path, _ = self.make_files(schema='other-index')

        with self.assertRaises(ValueError):
            self.read(manifest_name, index_path)

    def test_oversized_manifest_is_rejected_before_parsing(self):
        manifest_name, index_path, _ = self.make_files()

        with patch.object(self.storage, 'MAX_INDEX_MANIFEST_BYTES', 10):
            with self.assertRaises(ValueError):
                self.read(manifest_name, index_path)

    def test_symlinked_index_is_rejected(self):
        manifest_name, index_path, _ = self.make_files()
        target = self.root / 'other.json'
        index_path.rename(target)
        index_path.symlink_to(target)

        with self.assertRaises(ValueError):
            self.read(manifest_name, index_path)


class SessionReplayIndexAPITests(SimpleTestCase):
    def setUp(self):
        self.session = SimpleNamespace(id=uuid.uuid4(), asset_id=uuid.uuid4())
        self.path = reverse('api-terminal:session-replay-index',
                            kwargs={'pk': self.session.id})
        self.user = Mock()
        self.user.id = uuid.uuid4()
        self.user.is_authenticated = True
        self.user.is_anonymous = False
        self.user.has_perms.return_value = True

    def request(self, permitted=True):
        self.user.has_perms.return_value = permitted
        request = APIRequestFactory().get(self.path)
        force_authenticate(request, user=self.user)
        view = SessionReplayViewSet.as_view({'get': 'index'})
        return view(request, pk=self.session.id)

    @patch('terminal.api.session.session.get_object_or_404')
    @patch('terminal.api.session.session.SessionPartReplayStorageHandler')
    def test_authorized_read_returns_private_json(self, storage_cls, get_session):
        get_session.return_value = self.session
        storage_cls.return_value.get_verified_index_bytes.return_value = b'{"version":1}'
        storage_cls.INDEX_MEDIA_TYPE = 'application/vnd.jumpserver.recording-index+json'

        with patch.object(SessionReplayViewSet, '_record_replay_view') as audit:
            response = self.request()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'{"version":1}')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.user.has_perms.assert_called_with(['terminal.view_sessionreplay'])
        audit.assert_called_once()

    @patch('terminal.api.session.session.get_object_or_404')
    def test_denied_user_cannot_read_index(self, get_session):
        response = self.request(permitted=False)

        self.assertEqual(response.status_code, 403)
        get_session.assert_not_called()

    @patch('terminal.api.session.session.get_object_or_404')
    @patch('terminal.api.session.session.SessionPartReplayStorageHandler')
    def test_missing_index_returns_404(self, storage_cls, get_session):
        get_session.return_value = self.session
        storage_cls.return_value.get_verified_index_bytes.side_effect = FileNotFoundError()

        response = self.request()

        self.assertEqual(response.status_code, 404)

    @patch('terminal.api.session.session.get_object_or_404')
    @patch.object(SessionPartReplayStorageHandler, 'get_part_file_path_url',
                  return_value=(None, 'replay manifest not found'))
    def test_ce_replay_without_manifest_returns_404(self, _get_part, get_session):
        get_session.return_value = self.session

        response = self.request()

        self.assertEqual(response.status_code, 404)

    @patch('terminal.api.session.session.get_object_or_404')
    def test_ce_manifest_without_index_field_returns_404(self, get_session):
        get_session.return_value = self.session
        with tempfile.TemporaryDirectory() as directory:
            manifest_name = '{}.replay.json'.format(self.session.id)
            Path(directory, manifest_name).write_text(json.dumps({
                'type': 'mp4',
                'files': [{'name': '{}.0.part.mp4'.format(self.session.id), 'size': 100}],
            }))
            with (
                    patch('common.storage.replay.default_storage',
                          SimpleNamespace(base_location=directory)),
                    patch.object(SessionPartReplayStorageHandler, 'get_part_file_path_url',
                                 return_value=(manifest_name, '')),
            ):
                response = self.request()

        self.assertEqual(response.status_code, 404)

    @patch('terminal.api.session.session.get_object_or_404')
    def test_declared_but_missing_sidecar_returns_422(self, get_session):
        get_session.return_value = self.session
        with tempfile.TemporaryDirectory() as directory:
            manifest_name = '{}.replay.json'.format(self.session.id)
            Path(directory, manifest_name).write_text(json.dumps({
                'type': 'mp4',
                'files': [{'name': '{}.0.part.mp4'.format(self.session.id), 'size': 100}],
                'index': {
                    'schema': SessionPartReplayStorageHandler.INDEX_SCHEMA,
                    'schema_version': 1,
                    'name': '{}.index.v1.json'.format(self.session.id),
                    'media_type': SessionPartReplayStorageHandler.INDEX_MEDIA_TYPE,
                    'size': 10,
                    'sha256': '0' * 64,
                },
            }))
            with (
                    patch('common.storage.replay.default_storage',
                          SimpleNamespace(base_location=directory)),
                    patch.object(SessionPartReplayStorageHandler, 'get_part_file_path_url',
                                 return_value=(manifest_name, '')),
                    patch.object(SessionPartReplayStorageHandler, '_get_verified_index_path',
                                 side_effect=FileNotFoundError('missing sidecar')),
            ):
                response = self.request()

        self.assertEqual(response.status_code, 422)

    @patch('terminal.api.session.session.get_object_or_404')
    @patch('terminal.api.session.session.SessionPartReplayStorageHandler')
    def test_invalid_index_returns_422(self, storage_cls, get_session):
        get_session.return_value = self.session
        storage_cls.return_value.get_verified_index_bytes.side_effect = ValueError('hash mismatch')

        response = self.request()

        self.assertEqual(response.status_code, 422)
