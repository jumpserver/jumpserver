from django.test import SimpleTestCase

from assets.models import Asset, Platform


class AssetIconSkinTests(SimpleTestCase):
    """资产图标皮肤，需与 luna 的 iconMap 取值保持一致。"""

    @staticmethod
    def get_skin(name, platform_type, category='host'):
        platform = Platform(name=name, type=platform_type, category=category)
        asset = Asset(name='demo', address='127.0.0.1', platform=platform)
        return asset.get_icon_skin()

    def test_builtin_macos_platform_uses_macos_skin(self):
        # 内置 macOS 平台的 type 是 unix，只能按平台名识别
        self.assertEqual(self.get_skin('macOS', 'unix'), 'macos')

    def test_custom_macos_platform_uses_macos_skin(self):
        self.assertEqual(self.get_skin('My Mac', 'macos'), 'macos')

    def test_unix_platforms_keep_unix_skin(self):
        for name in ('Unix', 'BSD', 'AIX'):
            with self.subTest(name=name):
                self.assertEqual(self.get_skin(name, 'unix'), 'unix')

    def test_other_platforms_keep_type_skin(self):
        for name, platform_type in (('Linux', 'linux'), ('Windows', 'windows')):
            with self.subTest(name=name):
                self.assertEqual(self.get_skin(name, platform_type), platform_type)

    def test_device_category_uses_switch_skin(self):
        self.assertEqual(self.get_skin('Cisco', 'unix', category='device'), 'switch')

    def test_unknown_type_falls_back_to_file(self):
        self.assertEqual(self.get_skin('Custom', 'weird'), 'file')
