import os
import tempfile
from unittest.mock import patch

from django.test import TestCase

from assets.models import Platform, PlatformPackage


class PlatformPackageTestCase(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.storage_path = patch(
            'assets.models.platform.default_storage.path',
            side_effect=lambda path: os.path.join(self.media_dir.name, path),
        )
        self.storage_path.start()

    def tearDown(self):
        self.storage_path.stop()
        self.media_dir.cleanup()
        super().tearDown()

    def test_package_path_does_not_depend_on_platform_name(self):
        package = PlatformPackage.objects.create(name='Demo')
        platform = Platform.objects.create(name='Demo', package=package)
        package_dir = package.path
        os.makedirs(package_dir)
        with open(os.path.join(package_dir, 'platform.yml'), 'w'):
            pass

        platform.name = 'Renamed'
        platform.save(update_fields=['name'])

        self.assertTrue(platform.package.exists)
        self.assertEqual(package.path, package_dir)

    def test_cloned_platform_can_share_package(self):
        package = PlatformPackage.objects.create(name='Demo')
        source = Platform.objects.create(name='Demo', package=package)
        clone = Platform.objects.create(name='DemoClone', package=source.package)

        self.assertEqual(clone.package_id, source.package_id)
        self.assertEqual(package.platforms.count(), 2)

    @patch('assets.models.PlatformPackage.load_automation_methods')
    def test_shared_package_automation_is_loaded_once(self, loader):
        loader.return_value = [{'id': 'demo'}]
        package = PlatformPackage.objects.create(name='Demo')
        os.makedirs(package.path)
        with open(package.manifest_path, 'w'):
            pass
        Platform.objects.create(
            name='Demo', category='custom', type='demo', package=package,
        )
        Platform.objects.create(
            name='DemoClone', category='custom', type='demo', package=package,
        )

        methods = PlatformPackage.get_all_automation_methods()

        self.assertEqual(methods, [{'id': 'demo'}])
        loader.assert_called_once()

    @patch('assets.models.PlatformPackage.get_existing_automation_methods', return_value=[])
    def test_applet_platform_manifest_without_automations_is_valid(self, _existing):
        manifest = os.path.join(self.media_dir.name, 'platform.yml')
        with open(manifest, 'w', encoding='utf8') as stream:
            stream.write(
                'name: MySQLWorkbench\n'
                'category: custom\n'
                'type: DB\n'
                'protocols:\n'
                '  - name: mysqlworkbench\n'
                '    port: 0\n'
                '    primary: true\n'
                'custom_fields:\n'
                '  - name: db_name\n'
                '    label: DB Name\n'
                '    type: str\n'
            )

        data = PlatformPackage.validate(self.media_dir.name)

        self.assertEqual(data['name'], 'MySQLWorkbench')
