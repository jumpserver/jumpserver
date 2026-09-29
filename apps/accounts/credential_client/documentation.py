"""SDK documentation selection, independent of programming and UI languages."""

from pathlib import Path

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

SDK_LANGUAGES = {
    'python': {'label': 'Python', 'example': 'demo.py', 'runtime': 'Python 3.9+', 'credential_policies': True},
    'go': {'label': 'Go', 'example': 'cmd/demo/main.go', 'runtime': 'Go 1.23+', 'credential_policies': True},
    'java': {'label': 'Java', 'example': 'src/main/java/org/jumpserver/pam/Demo.java', 'runtime': 'Java 11+', 'credential_policies': True},
    'node': {'label': 'Node.js', 'example': 'demo.js', 'runtime': 'Node.js 20.3+', 'credential_policies': True},
    'curl': {'label': 'cURL', 'example': 'demo.sh', 'runtime': 'Bash / cURL / OpenSSL', 'credential_policies': False},
}
DOCUMENTATION_LANGUAGES = ('en', 'zh-hans', 'zh-hant', 'ja', 'ko', 'pt-br', 'ru', 'vi', 'es', 'fr')
LANGUAGE_ALIASES = {
    'zh': 'zh-hans', 'zh-cn': 'zh-hans', 'zh-sg': 'zh-hans',
    'zh-tw': 'zh-hant', 'zh-hk': 'zh-hant', 'zh-mo': 'zh-hant',
    'pt': 'pt-br',
}


def documentation_language(language):
    language = (language or 'en').replace('_', '-').lower()
    language = LANGUAGE_ALIASES.get(language, language)
    if language in DOCUMENTATION_LANGUAGES:
        return language
    prefix = '-'.join(language.split('-')[:2])
    if prefix in DOCUMENTATION_LANGUAGES:
        return prefix
    base = language.split('-')[0]
    base = LANGUAGE_ALIASES.get(base, base)
    return base if base in DOCUMENTATION_LANGUAGES else 'en'


def get_sdk_documentation(sdk_language, language):
    if sdk_language not in SDK_LANGUAGES:
        raise ValidationError({'language': _('Unsupported SDK language.')})
    definition = SDK_LANGUAGES[sdk_language]
    locale = documentation_language(language)
    directory = Path(settings.APPS_DIR) / 'accounts' / 'clients' / sdk_language
    path = directory / f'README.{locale}.md'
    if not path.is_file():
        locale = 'en'
        path = directory / 'README.en.md'
    return {
        'language': sdk_language,
        'documentation_language': locale,
        'languages': [
            {'value': key, 'label': value['label']}
            for key, value in SDK_LANGUAGES.items() if value['credential_policies']
        ],
        'runtime': definition['runtime'],
        'credential_policies': definition['credential_policies'],
        'readme': path.read_text(encoding='utf-8'),
        'code': (directory / definition['example']).read_text(encoding='utf-8'),
    }
