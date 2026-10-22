import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from ops.api.playbook import PlaybookFileViewSet
from ops.models import Playbook


class PlaybookFileBoundaryTests(SimpleTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.directory = self.base / 'playbook'
        self.directory.mkdir()
        self.outside = self.base / 'outside.yml'
        self.outside.write_text('outside')
        self.factory = APIRequestFactory()
        self.playbook = SimpleNamespace(work_dir=str(self.directory), name='example')
        self.api = PlaybookFileViewSet.as_view(
            {
                'get': 'retrieve',
                'post': 'create',
                'patch': 'partial_update',
                'delete': 'destroy',
            },
            authentication_classes=[],
            permission_classes=[],
            throttle_classes=[],
        )

    def call(self, method, data):
        if method in {'get', 'delete'}:
            request = getattr(self.factory, method)('/?' + urlencode(data))
        else:
            request = getattr(self.factory, method)('/', data, format='json')
        with (
            patch.object(PlaybookFileViewSet, 'get_playbook', return_value=self.playbook),
            patch('ops.api.playbook.get_object_or_404', return_value=self.playbook),
        ):
            return self.api(request, pk='00000000-0000-0000-0000-000000000001')

    def test_entry_aliases_cannot_be_renamed_or_deleted(self):
        for name in Playbook.entry_filenames:
            entry = self.directory / name
            entry.write_text('entry')
            for key in (name, './' + name, 'root/' + name, 'tasks/../' + name):
                for method in ('patch', 'delete'):
                    with self.subTest(key=key, method=method):
                        response = self.call(method, {'key': key, 'new_name': 'renamed.yml'})
                        self.assertEqual(response.status_code, 400)
                        self.assertEqual(entry.read_text(), 'entry')
                        self.assertFalse((self.directory / 'renamed.yml').exists())

    def test_root_aliases_cannot_be_edited_renamed_or_deleted(self):
        entry = self.directory / 'main.yml'
        entry.write_text('entry')
        for key in ('root', '.', './', 'root/', 'tasks/..'):
            for method, extra in (
                ('patch', {'content': 'changed'}),
                ('patch', {'new_name': 'renamed'}),
                ('delete', {}),
            ):
                with self.subTest(key=key, method=method, extra=extra):
                    response = self.call(method, {'key': key, **extra})
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(entry.read_text(), 'entry')

    def test_entry_content_remains_editable(self):
        for name in Playbook.entry_filenames:
            with self.subTest(name=name):
                entry = self.directory / name
                entry.write_text('entry')
                response = self.call('patch', {'key': 'root/./' + name, 'content': 'updated'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(entry.read_text(), 'updated')

    def test_paths_cannot_escape_the_playbook(self):
        keys = (
            '../outside.yml',
            str(self.outside),
            str(self.directory / 'tasks.yml'),
            'root/../../outside.yml',
            'tasks\x00.yml',
            'tasks\\outside.yml',
        )
        for key in keys:
            for method in ('get', 'post', 'patch', 'delete'):
                with self.subTest(key=key, method=method):
                    response = self.call(method, {'key': key, 'name': 'new.yml', 'content': 'changed'})
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(self.outside.read_text(), 'outside')
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_leaf_names_cannot_contain_paths(self):
        source = self.directory / 'tasks.yml'
        source.write_text('tasks')
        for name in (
            '.',
            '..',
            'root',
            '../outside.yml',
            'tasks/new.yml',
            'tasks\\new.yml',
            'new\x00.yml',
        ):
            for method, data in (
                ('post', {'name': name}),
                ('patch', {'key': 'tasks.yml', 'new_name': name}),
            ):
                with self.subTest(method=method, name=name):
                    response = self.call(method, data)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(source.read_text(), 'tasks')
                    self.assertEqual(self.outside.read_text(), 'outside')

    def test_symlink_paths_cannot_be_accessed(self):
        (self.directory / 'external.yml').symlink_to(self.outside)
        (self.directory / 'external-dir').symlink_to(self.base, target_is_directory=True)
        (self.directory / 'broken.yml').symlink_to(self.base / 'missing.yml')
        (self.directory / 'tasks.yml').write_text('tasks')
        (self.directory / 'internal.yml').symlink_to(self.directory / 'tasks.yml')
        for key in (
            'external.yml',
            'external-dir/outside.yml',
            'broken.yml',
            'internal.yml',
        ):
            for method in ('get', 'post', 'patch', 'delete'):
                with self.subTest(key=key, method=method):
                    response = self.call(method, {'key': key, 'name': 'new.yml', 'content': 'changed'})
                    self.assertEqual(response.status_code, 400)
        self.assertEqual(self.outside.read_text(), 'outside')
        self.assertEqual((self.directory / 'tasks.yml').read_text(), 'tasks')
        self.assertFalse((self.base / 'missing.yml').exists())

    def test_symlink_work_directory_cannot_be_accessed(self):
        root_link = self.base / 'linked-playbook'
        root_link.symlink_to(self.directory, target_is_directory=True)
        self.playbook.work_dir = str(root_link)
        for method in ('get', 'post', 'patch', 'delete'):
            with self.subTest(method=method):
                response = self.call(method, {'key': 'tasks.yml', 'content': 'changed'})
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.call('get', {}).status_code, 400)

    def test_symlink_rename_destination_is_rejected(self):
        source = self.directory / 'tasks.yml'
        source.write_text('tasks')
        for target in (self.outside, self.base / 'missing.yml'):
            destination = self.directory / 'destination.yml'
            destination.symlink_to(target)
            response = self.call('patch', {'key': 'tasks.yml', 'new_name': destination.name})
            self.assertEqual(response.status_code, 400)
            self.assertTrue(destination.is_symlink())
            self.assertEqual(source.read_text(), 'tasks')
            destination.unlink()

    def test_created_keys_work_for_nested_and_hidden_directories(self):
        for name in ('roles', '.roles'):
            with self.subTest(name=name):
                self.assertEqual(
                    self.call('post', {'name': name, 'is_directory': True}).status_code,
                    200,
                )
                created = self.call(
                    'post',
                    {'key': 'root/' + name, 'name': 'tasks.yml', 'content': 'tasks'},
                )
                self.assertEqual(created.status_code, 200)
                self.assertEqual(created.data['id'], name + '/tasks.yml')
                self.assertEqual(created.data['pId'], name)
                key = created.data['id']
                self.assertEqual(self.call('get', {'key': key}).data, {'content': 'tasks'})
                self.assertEqual(
                    self.call('patch', {'key': key, 'content': 'updated'}).status_code,
                    200,
                )
                self.assertEqual((self.directory / key).read_text(), 'updated')
                tree = self.call('get', {}).data
                node = next(node for node in tree if node['id'] == key)
                self.assertEqual(node['pId'], name)
                self.assertEqual(self.call('delete', {'key': key}).status_code, 200)

    def test_tree_omits_symlinks(self):
        (self.directory / 'external.yml').symlink_to(self.outside)
        (self.directory / 'external-dir').symlink_to(self.base, target_is_directory=True)
        (self.directory / 'tasks.yml').write_text('tasks')
        response = self.call('get', {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([node['id'] for node in response.data], ['root', 'tasks.yml'])

    def test_content_edits_preserve_permission_bits(self):
        source = self.directory / 'tasks.yml'
        for mode in (0o600, 0o640, 0o644, 0o755):
            with self.subTest(mode=oct(mode)):
                source.write_text('original')
                source.chmod(mode)
                response = self.call('patch', {'key': source.name, 'content': 'updated'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(source.read_text(), 'updated')
                self.assertEqual(stat.S_IMODE(source.stat().st_mode), mode)

    def test_failed_atomic_replace_preserves_original_content(self):
        source = self.directory / 'tasks.yml'
        source.write_text('original')
        with (
            patch('common.utils.yml.os.replace', side_effect=OSError('replace failed')),
            self.assertRaises(OSError),
        ):
            self.call('patch', {'key': source.name, 'content': 'updated'})
        self.assertEqual(source.read_text(), 'original')
        self.assertEqual(list(self.directory.iterdir()), [source])

    def test_exclusive_creation_preserves_a_concurrent_file(self):
        source = self.directory / 'tasks.yml'
        original_open = open

        def create_concurrently(path, mode='r', *args, **kwargs):
            if mode == 'x':
                Path(path).write_text('concurrent content')
            return original_open(path, mode, *args, **kwargs)

        with patch('builtins.open', side_effect=create_concurrently):
            response = self.call('post', {'name': source.name, 'content': 'updated'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(source.read_text(), 'concurrent content')

    def test_duplicate_creation_preserves_existing_files(self):
        for content in ('first', 'second'):
            response = self.call('post', {'name': 'tasks.yml', 'content': content})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                self.call('get', {'key': response.data['id']}).data,
                {'content': content},
            )
        self.assertEqual((self.directory / 'tasks.yml').read_text(), 'first')
