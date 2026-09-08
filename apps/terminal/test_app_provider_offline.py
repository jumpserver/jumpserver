import errno
import json
import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, override_settings

from terminal.automations.deploy_app_provider import DeployAppProviderManager, default_panda_image, stage_resources
from terminal.serializers.virtualapp_provider import AppProviderDeployOptionsSerializer


class OfflineProviderResourcesTests(SimpleTestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(override_settings(DATA_DIR=self.directory))
        self.resources = Path(self.directory) / 'virtualapp'
        self.resources.mkdir()
        self.image = 'jumpserver/panda:v5.0-ee'
        self.metadata = {
            'image': self.image, 'architecture': 'amd64',
            'image_id': 'sha256:' + '1' * 64, 'sha256': '2' * 64, 'file': 'panda.zst',
        }

    def write_manifest(self):
        (self.resources / 'manifest.json').write_text(json.dumps({'panda': self.metadata}))

    def test_missing_bundle_requires_explicit_image_instead_of_latest(self):
        self.assertEqual(default_panda_image(), '')
        self.assertEqual(stage_resources(Path(self.directory) / 'task', self.image), {'panda': {}, 'docker': {}})

    def test_malformed_manifest_keeps_form_readable_but_blocks_staging(self):
        (self.resources / 'manifest.json').write_text('{invalid')
        self.assertEqual(default_panda_image(), '')
        with self.assertRaises(ValueError):
            stage_resources(Path(self.directory) / 'task', self.image)

    def test_options_default_and_cleared_override_use_exact_bundle_image(self):
        self.write_manifest()
        for options in ({}, {'PANDA_IMAGE': ''}):
            serializer = AppProviderDeployOptionsSerializer(data={
                'CORE_HOST': 'https://core.example.com', **options,
            })
            serializer.is_valid(raise_exception=True)
            self.assertEqual(serializer.validated_data['PANDA_IMAGE'], self.image)

    def test_staged_archive_remains_readable_after_installer_replaces_source(self):
        self.write_manifest()
        source = self.resources / 'panda.zst'
        source.write_bytes(b'offline archive')
        staged = stage_resources(Path(self.directory) / 'task', self.image)['panda']
        self.assertEqual(os.stat(staged['file']).st_ino, source.stat().st_ino)
        replacement = self.resources / 'new.zst'
        replacement.write_bytes(b'new archive')
        os.replace(replacement, source)
        self.assertEqual(Path(staged['file']).read_bytes(), b'offline archive')
        staged = stage_resources(Path(self.directory) / 'next-task', self.image)['panda']
        source.unlink()
        self.assertEqual(Path(staged['file']).read_bytes(), b'new archive')

    def test_archive_removed_during_staging_preserves_identity_for_local_reuse(self):
        self.write_manifest()
        source = self.resources / 'panda.zst'
        link, copyfile = os.link, shutil.copyfile

        for cross_device in (False, True):
            with self.subTest(cross_device=cross_device):
                source.write_bytes(b'offline archive')

                def stage_archive(src, dst):
                    source.unlink()
                    return (copyfile if cross_device else link)(src, dst)

                with mock.patch('os.link', side_effect=(
                    OSError(errno.EXDEV, 'Cross-device link') if cross_device else stage_archive
                )), mock.patch('shutil.copyfile', side_effect=stage_archive):
                    staged = stage_resources(Path(self.directory) / 'task', self.image)['panda']

                self.assertEqual(staged, {**self.metadata, 'file': ''})

    def test_staging_does_not_ignore_other_io_errors(self):
        self.write_manifest()
        (self.resources / 'panda.zst').write_bytes(b'offline archive')
        with mock.patch('os.link', side_effect=PermissionError('Permission denied')):
            with self.assertRaises(PermissionError):
                stage_resources(Path(self.directory) / 'task', self.image)

    def test_missing_archive_preserves_identity_for_local_reuse(self):
        self.write_manifest()
        staged = stage_resources(Path(self.directory) / 'task', self.image)['panda']
        self.assertEqual(staged['file'], '')
        self.assertEqual(staged['image_id'], self.metadata['image_id'])

    def test_docker_service_snapshot_survives_installer_updates(self):
        metadata = {'architecture': 'amd64', 'sha256': '3' * 64, 'file': 'docker.tar.gz'}
        (self.resources / 'manifest.json').write_text(json.dumps({'docker': metadata}))
        (self.resources / 'docker.tar.gz').write_bytes(b'docker archive')
        service = self.resources / 'docker.service'
        link = os.link
        for cross_device in (False, True):
            with self.subTest(cross_device=cross_device):
                service.write_bytes(b'installer service')
                with mock.patch('os.link', side_effect=(
                    OSError(errno.EXDEV, 'Cross-device link') if cross_device else link
                )):
                    staged = stage_resources(
                        Path(self.directory) / f'task-{cross_device}', self.image,
                    )['docker']
                replacement = self.resources / 'new.service'
                replacement.write_bytes(b'updated installer service')
                os.replace(replacement, service)
                self.assertEqual(Path(staged['service']).read_bytes(), b'installer service')
                self.assertEqual(Path(staged['file']).read_bytes(), b'docker archive')

    def test_missing_docker_service_keeps_archive_available_for_runtime_check(self):
        metadata = {'architecture': 'amd64', 'sha256': '3' * 64, 'file': 'docker.tar.gz'}
        (self.resources / 'manifest.json').write_text(json.dumps({'docker': metadata}))
        (self.resources / 'docker.tar.gz').write_bytes(b'docker archive')
        staged = stage_resources(Path(self.directory) / 'task', self.image)['docker']
        self.assertEqual(staged['service'], '')
        self.assertEqual(Path(staged['file']).read_bytes(), b'docker archive')

    def test_custom_image_does_not_use_bundle_identity(self):
        self.write_manifest()
        staged = stage_resources(Path(self.directory) / 'task', 'custom/panda:v1')
        self.assertEqual(staged['panda'], {})

    def test_archive_path_cannot_escape_resource_directory(self):
        self.metadata['file'] = '../outside.zst'
        self.write_manifest()
        with self.assertRaisesMessage(ValueError, 'archive path'):
            stage_resources(Path(self.directory) / 'task', self.image)

    def test_success_requires_exact_image_confirmation_from_the_task(self):
        app = SimpleNamespace(image_name='app:v1', version='1.0')
        for image in (None, {'name': 'app:v1', 'version': 'old', 'id': 'sha256:' + '1' * 64}):
            tasks = {} if image is None else {'image': {'res': {
                'ansible_stats': {'data': {'virtual_app_image': image}},
            }}}
            result = SimpleNamespace(result={'ok': {'provider': tasks}})
            with self.assertRaises(ValueError):
                DeployAppProviderManager.get_published_image_id(result, app)
