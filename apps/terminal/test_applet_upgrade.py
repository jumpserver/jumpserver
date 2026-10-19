import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile

import yaml
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from terminal.api.applet.applet import AppletViewSet
from terminal.applets import install_or_update_builtin_applets
from terminal.models import Applet


class AppletUpgradeTests(SimpleTestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        self.apps_dir = root / 'apps'
        self.media_dir = root / 'media'
        self.enterContext(self.settings(
            APPS_DIR=str(self.apps_dir), MEDIA_ROOT=str(self.media_dir),
        ))

    def package(self, name, builtin=False, version='0.4'):
        root = self.apps_dir / 'terminal' if builtin else self.media_dir
        path = root / 'applets' / name
        path.mkdir(parents=True)
        (path / 'manifest.yml').write_text(yaml.safe_dump({'name': name, 'version': version}))
        (path / 'setup.yml').write_text('type: exe\n')
        (path / 'app.py').write_text('# applet entry point\n')
        (path / 'icon.png').write_bytes(b'icon')
        (path / 'README.md').write_text('Existing applet')
        return path

    def download(self, applet):
        view = AppletViewSet()
        with patch.object(view, 'get_object', return_value=applet):
            return view.download(None)

    def test_removed_builtin_can_be_downloaded_again_from_persisted_package(self):
        for name in ('dbeaver', 'chrome'):
            with self.subTest(name=name):
                path = self.package(name)
                applet = Applet(name=name, builtin=True)

                response = self.download(applet)

                self.assertEqual(response.status_code, 200)
                with ZipFile(io.BytesIO(response.content)) as archive:
                    self.assertEqual(archive.read('app.py'), (path / 'app.py').read_bytes())
                    self.assertEqual(yaml.safe_load(archive.read('manifest.yml'))['name'], name)
                self.assertFalse(path.with_suffix('.zip').exists())
                self.assertTrue((path / 'app.py').exists())
                self.assertEqual(applet.path, str(path))
                self.assertEqual(applet.manifest['version'], '0.4')
                self.assertEqual(applet.readme, 'Existing applet')
                self.assertIsNotNone(applet.icon)

    def test_current_builtin_prefers_release_package_over_stored_copy(self):
        self.package('dbx', version='old')
        path = self.package('dbx', builtin=True, version='new')
        applet = Applet(name='dbx', builtin=True)

        self.assertEqual(applet.path, str(path))
        with ZipFile(io.BytesIO(self.download(applet).content)) as archive:
            self.assertEqual(yaml.safe_load(archive.read('manifest.yml'))['version'], 'new')

    def test_uploaded_applet_always_uses_uploaded_package(self):
        self.package('dbx', builtin=True, version='builtin')
        path = self.package('dbx', version='uploaded')
        applet = Applet(name='dbx', builtin=False)

        self.assertEqual(applet.path, str(path))
        with ZipFile(io.BytesIO(self.download(applet).content)) as archive:
            self.assertEqual(yaml.safe_load(archive.read('manifest.yml'))['version'], 'uploaded')

    def test_missing_persisted_package_still_reports_installation_error(self):
        with self.assertRaises(ValidationError) as raised:
            self.download(Applet(name='dbeaver', builtin=True))

        self.assertIn(str(self.media_dir / 'applets' / 'dbeaver'), str(raised.exception))

    def test_fresh_install_includes_dbx_without_reintroducing_dbeaver(self):
        with patch.object(Applet, 'install_from_dir') as install:
            install_or_update_builtin_applets()

        names = [Path(call.args[0]).name for call in install.call_args_list]
        self.assertIn('dbx', names)
        self.assertNotIn('dbeaver', names)
