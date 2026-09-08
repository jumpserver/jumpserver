import os
import tempfile

from django.test import SimpleTestCase

from assets.utils.platform_package import locate_package_root
from terminal.models import Applet, VirtualApp


class PackageRootLocateTests(SimpleTestCase):
    def make_file(self, base_dir, relative_path):
        path = os.path.join(base_dir, relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf8') as f:
            f.write('test')
        return path

    def test_locate_package_root_supports_files_extracted_to_current_dir(self):
        with tempfile.TemporaryDirectory() as extract_to:
            self.make_file(extract_to, 'manifest.yml')
            self.make_file(extract_to, 'icon.png')

            root = locate_package_root(extract_to, 'demo.zip', 'manifest.yml')

            self.assertEqual(root, extract_to)

    def test_locate_package_root_supports_single_wrapped_directory(self):
        with tempfile.TemporaryDirectory() as extract_to:
            wrapped_dir = os.path.join(extract_to, 'demo')
            self.make_file(wrapped_dir, 'manifest.yml')
            self.make_file(wrapped_dir, 'icon.png')

            root = locate_package_root(extract_to, 'demo.zip', 'manifest.yml')

            self.assertEqual(root, wrapped_dir)

    def test_applet_locate_pkg_root_supports_files_extracted_to_current_dir(self):
        with tempfile.TemporaryDirectory() as extract_to:
            self.make_file(extract_to, 'manifest.yml')

            root = Applet.locate_pkg_root(extract_to, 'demo.zip')

            self.assertEqual(root, extract_to)

    def test_virtualapp_locate_pkg_root_supports_files_extracted_to_current_dir(self):
        with tempfile.TemporaryDirectory() as extract_to:
            self.make_file(extract_to, 'manifest.yml')

            root = VirtualApp.locate_pkg_root(extract_to, 'demo.zip')

            self.assertEqual(root, extract_to)


class WebAppletDefaultsTests(SimpleTestCase):
    def test_builtin_install_skips_chrome_and_includes_web_applet(self):
        from unittest.mock import patch
        from terminal.applets import install_or_update_builtin_applets

        with patch.object(Applet, 'install_from_dir', return_value=None) as install:
            install_or_update_builtin_applets()
        names = [os.path.basename(call.args[0]) for call in install.call_args_list]
        self.assertIn('weblite', names)
        self.assertNotIn('chrome', names)

    def test_direct_mode_is_default_and_recording_endpoint_is_optional(self):
        from terminal.serializers.applet_host import DeployOptionsSerializer

        serializer = DeployOptionsSerializer(data={})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertFalse(serializer.validated_data['WEB_APPLET_RECORDING_ENABLED'])
        self.assertEqual(serializer.validated_data['WEB_PROXY_URL'], '')
        enabled = DeployOptionsSerializer(data={'WEB_APPLET_RECORDING_ENABLED': True})
        self.assertFalse(enabled.is_valid())
        self.assertIn('WEB_PROXY_URL', enabled.errors)
