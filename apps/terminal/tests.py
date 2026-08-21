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
