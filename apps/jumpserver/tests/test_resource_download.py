import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from jumpserver.views.other import ResourceDownload


class ResourceDownloadTestCase(SimpleTestCase):
    def test_client_version_comes_from_runtime_version_file(self):
        with TemporaryDirectory() as data_dir:
            Path(data_dir, 'version.txt').write_text(
                'TINKER_VERSION=v0.2.3\nCLIENT_VERSION=5.0.1\n'
            )
            with self.settings(DATA_DIR=data_dir):
                meta = ResourceDownload().get_meta_json()

        self.assertEqual(meta['CLIENT_VERSION'], '5.0.1')

    def test_environment_can_override_runtime_client_version(self):
        with TemporaryDirectory() as data_dir:
            Path(data_dir, 'version.txt').write_text('CLIENT_VERSION=5.0.1\n')
            with self.settings(DATA_DIR=data_dir):
                with patch.dict(os.environ, {'CLIENT_VERSION': '5.0.2'}):
                    meta = ResourceDownload().get_meta_json()

        self.assertEqual(meta['CLIENT_VERSION'], '5.0.2')

    def test_default_client_version_is_available_without_runtime_file(self):
        with TemporaryDirectory() as data_dir:
            with self.settings(DATA_DIR=data_dir):
                with patch.dict(os.environ, {'CLIENT_VERSION': ''}):
                    meta = ResourceDownload().get_meta_json()

        self.assertEqual(meta['CLIENT_VERSION'], '4.1.6')
