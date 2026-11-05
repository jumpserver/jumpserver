import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.template import Context, Engine
from django.test import SimpleTestCase, override_settings

from jumpserver.views.other import ResourceDownload


@override_settings(VERSION='v5.1.0')
class ResourceDownloadTestCase(SimpleTestCase):
    def test_shared_client_version_takes_priority_over_core_and_environment(self):
        with TemporaryDirectory() as data_dir:
            Path(data_dir, 'version.txt').write_text(
                'TINKER_VERSION=v0.2.3\nCLIENT_VERSION=5.0.0\n'
            )
            with self.settings(DATA_DIR=data_dir), patch.dict(os.environ, {'CLIENT_VERSION': '5.0.2'}):
                meta = ResourceDownload().get_meta_json()

        self.assertEqual(meta['CLIENT_VERSION'], '5.0.0')
        self.assertEqual(meta['TINKER_VERSION'], 'v0.2.3')

    def test_local_default_follows_core_without_shared_version_file(self):
        with TemporaryDirectory() as data_dir, self.settings(DATA_DIR=data_dir), \
                patch.dict(os.environ, {'CLIENT_VERSION': '5.0.2'}):
            meta = ResourceDownload().get_meta_json()

        self.assertEqual(meta['CLIENT_VERSION'], '5.1.0')

    def test_client_uses_the_full_version(self):
        with TemporaryDirectory() as data_dir, self.settings(DATA_DIR=data_dir):
            for version, expected in (
                ('v5.2.3', '5.2.3'), ('5.2.3', '5.2.3'),
                ('v5.1.0-rc', '5.1.0-rc'), ('v5.1.0-rc1', '5.1.0-rc1'),
                ('v5.1.0-rc.1', '5.1.0-rc.1'), ('v5.1.0-adasda', '5.1.0-adasda'),
            ):
                with self.subTest(version=version), self.settings(VERSION=version):
                    meta = ResourceDownload().get_meta_json()
                    self.assertEqual(meta['CLIENT_VERSION'], expected)

    def test_shared_client_versions_use_the_full_version(self):
        with TemporaryDirectory() as data_dir, self.settings(DATA_DIR=data_dir):
            for core_version, shared_version, expected in (
                ('v5.1.0', '5.2.3', '5.2.3'), ('v5.1.0', 'v5.2.3', '5.2.3'),
                ('v5.1.0', ' v5.2.3-rc.1 ', '5.2.3-rc.1'), ('', '5.2.3', '5.2.3'),
            ):
                with self.subTest(core=core_version, shared=shared_version), self.settings(VERSION=core_version):
                    Path(data_dir, 'version.txt').write_text(f'CLIENT_VERSION={shared_version}\n')
                    self.assertEqual(ResourceDownload().get_meta_json()['CLIENT_VERSION'], expected)

    def test_invalid_shared_versions_fall_back_to_full_core_version(self):
        with TemporaryDirectory() as data_dir, self.settings(DATA_DIR=data_dir, VERSION='v5.1.0-rc.1'):
            for version in ('', 'dev', '5.0', '../5.0.0', '5.0.0/invalid', '5.0.0-rc..1'):
                with self.subTest(version=version):
                    Path(data_dir, 'version.txt').write_text(f'CLIENT_VERSION={version}\n')
                    self.assertEqual(ResourceDownload().get_meta_json()['CLIENT_VERSION'], '5.1.0-rc.1')

    def test_dev_and_unavailable_versions_hide_downloads(self):
        with TemporaryDirectory() as data_dir, self.settings(DATA_DIR=data_dir):
            for version, shared_version in (
                ('dev', '5.1.0'), ('', 'invalid'), ('v5.1', ''), ('../5.1.0', ''), ('vv5.1.0', ''),
            ):
                with self.subTest(version=version), self.settings(VERSION=version):
                    Path(data_dir, 'version.txt').write_text(f'CLIENT_VERSION={shared_version}\n')
                    meta = ResourceDownload().get_meta_json()
                    self.assertEqual(meta['CLIENT_VERSION'], '')

    def test_page_links_to_selected_client_version_and_hides_dev_downloads(self):
        template_path = Path(__file__).resolve().parents[2] / 'templates/resource_download.html'
        engine = Engine(
            loaders=[('django.template.loaders.locmem.Loader', {
                '_without_nav_base.html': '{% block body %}{% endblock %}',
                'resource_download.html': template_path.read_text(),
            })],
            libraries={'i18n': 'django.templatetags.i18n', 'static': 'django.templatetags.static'},
        )
        template = engine.get_template('resource_download.html')
        with TemporaryDirectory() as data_dir, self.settings(DATA_DIR=data_dir):
            for version, shared_version, expected in (
                ('v5.1.0', '5.0.0', '5.0.0'), ('v5.1.0', 'v5.2.3-rc.1', '5.2.3-rc.1'),
                ('v5.1.0-rc', 'invalid', '5.1.0-rc'), ('v5.1.0-adasda', '', '5.1.0-adasda'),
                ('dev', '5.0.0', ''),
            ):
                with self.subTest(version=version, shared=shared_version), self.settings(VERSION=version):
                    Path(data_dir, 'version.txt').write_text(f'CLIENT_VERSION={shared_version}\n')
                    context = ResourceDownload().get_context_data()
                    html = template.render(Context(context))
                    if expected:
                        self.assertIn(f'/download/public/Client_{expected}_x64-setup.exe', html)
                        self.assertIn(f'/download/public/Client_{expected}_aarch64.dmg', html)
                        self.assertIn(f'Version {expected}', html)
                    else:
                        self.assertNotIn('/download/public/', html)
                        self.assertNotIn('download-version', html)
