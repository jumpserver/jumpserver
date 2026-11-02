import ast
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


APP_PATH = Path(__file__).resolve().parents[2] / 'apps/terminal/applets/chrome/app.py'


def load_language_code():
    tree = ast.parse(APP_PATH.read_text(encoding='utf-8'))
    names = {'CHROME_LANGUAGE_ALIASES', 'LANGUAGE_TAG_PATTERN'}
    nodes = [
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id in names for target in node.targets)
    ]
    nodes.extend(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {'to_chrome_language', 'default_chrome_driver_options'}
    )
    applet = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'AppletApplication')
    init = next(node for node in applet.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
    nodes.append(ast.ClassDef(name='AppletApplication', bases=[ast.Name(id='BaseApplication', ctx=ast.Load())],
                              keywords=[], body=[init], decorator_list=[]))

    class Options:
        def __init__(self):
            self.arguments = []
            self.experimental = {}

        def add_argument(self, value):
            self.arguments.append(value)

        def add_experimental_option(self, key, value):
            self.experimental[key] = value

    class BaseApplication:
        def __init__(self, **kwargs):
            self.connect_option = SimpleNamespace(lang=kwargs['lang'])
            self.asset = SimpleNamespace(address='https://example.invalid')
            self.platform = SimpleNamespace(get_protocol_setting=lambda protocol: None)
            self.app_name = self.user = self.account = None
            self.protocol = 'http'

    env = {
        're': re,
        'webdriver': SimpleNamespace(ChromeOptions=Options),
        'BaseApplication': BaseApplication,
        'WebAPP': Mock(),
        'tempfile': SimpleNamespace(TemporaryDirectory=lambda: SimpleNamespace(name='test-profile')),
        'get_system_language': Mock(return_value='zh_TW'),
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(APP_PATH), 'exec'), env)
    return env


class ChromeLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = load_language_code()

    def test_language_conversion(self):
        cases = {
            'zh-hans': 'zh-CN', ' zh_CN ': 'zh-CN', 'zh-SG': 'zh-CN',
            'zh-Hans-CN': 'zh-CN', 'zh-hant': 'zh-TW', 'zh_TW': 'zh-TW',
            'zh-Hant-HK': 'zh-TW', 'zh-HK': 'zh-TW', 'zh-MO': 'zh-TW',
            'en': 'en-US', 'en_US': 'en-US', 'en_GB': 'en-GB',
            'pt-br': 'pt-BR', 'ja_JP': 'ja-JP', 'ko_KR': 'ko-KR',
            'es': 'es', 'ru': 'ru', 'vi': 'vi', 'sr_latn_rs': 'sr-Latn-RS',
            '': 'en-US', ' ': 'en-US', 'en-US,zh-CN': 'en-US',
        }
        convert = self.env['to_chrome_language']
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(convert(raw), expected)
        for raw in (None, 123):
            with self.subTest(raw=raw):
                self.assertEqual(convert(raw), 'en-US')

    def test_options_use_converted_explicit_or_system_language(self):
        for raw, expected in [('zh-hans', 'zh-CN'), ('', 'zh-TW')]:
            with self.subTest(raw=raw):
                self.env['get_system_language'].reset_mock()
                options = self.env['AppletApplication'](lang=raw)._chrome_options
                self.assertIn('--lang=' + expected, options.arguments)
                self.assertEqual(options.experimental['prefs']['intl.accept_languages'], expected)
                self.assertIn('--user-data-dir=test-profile', options.arguments)
                self.assertEqual(self.env['get_system_language'].call_count, 0 if raw else 1)


if __name__ == '__main__':
    unittest.main()
