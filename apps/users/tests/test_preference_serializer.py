from django.test import SimpleTestCase
from django.utils import translation
from rest_framework.exceptions import ValidationError

from users.serializers.preference.lina import BasicSerializer
from users.serializers.preference.luna import LunaSerializer


class LanguageChoiceFieldTest(SimpleTestCase):
    def setUp(self):
        self.field = BasicSerializer().fields['lang']

    def test_representation_normalizes_language_aliases(self):
        aliases = {
            'zh': 'zh-hans',
            'zh-cn': 'zh-hans',
            'zh-tw': 'zh-hant',
            'zh-hk': 'zh-hant',
        }

        for alias, expected in aliases.items():
            with self.subTest(alias=alias):
                self.assertEqual(self.field.to_representation(alias), expected)

    def test_input_normalizes_language_aliases(self):
        self.assertEqual(self.field.run_validation('zh-cn'), 'zh-hans')
        self.assertEqual(self.field.run_validation('zh-tw'), 'zh-hant')

    def test_input_rejects_unknown_language(self):
        with self.assertRaises(ValidationError):
            self.field.run_validation('unknown')


class LunaPreferenceSectionLabelTest(SimpleTestCase):
    def test_labels_match_luna_navigation(self):
        expected = {
            'en': ('General', 'GUI', 'CLI'),
            'zh-hans': ('基本配置', '图形化', '命令行'),
            'zh-hant': ('基本配置', '圖形化', '命令行'),
            'ja': ('基本構成', 'グラフィカル', 'コマンドライン'),
            'ko': ('기본 설정', '그래픽화', '명령행'),
            'pt-br': ('Configurações Básicas', 'Gráfico', 'Linha de Comando'),
            'es': ('Configuración básica', 'Gráfico', 'Línea de comandos'),
            'ru': ('Основные настройки', 'Графический интерфейс', 'Командная строка'),
            'vi': ('Cấu hình cơ bản', 'Đồ họa', 'Dòng lệnh'),
        }

        for language, labels in expected.items():
            with self.subTest(language=language), translation.override(language):
                fields = LunaSerializer().fields
                actual = tuple(
                    str(fields[name].label)
                    for name in ('basic', 'graphics', 'command_line')
                )
                self.assertEqual(actual, labels)
