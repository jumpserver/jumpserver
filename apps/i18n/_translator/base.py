import asyncio
import json
import os
import re
import sys
from collections import Counter

from tqdm import tqdm

from .const import GREEN, RESET, YELLOW


class TranslationError(RuntimeError):
    pass


class BaseTranslateManager:
    bulk_size = 15
    max_concurrency = 4
    max_attempts = 3
    request_timeout = 120
    retry_delay = 1
    LANG_MAPPER = {
        'en': 'English',
        'ja': 'Japanese',
        'zh_Hant': 'Traditional Chinese',
        'pt_BR': 'Portuguese (Brazil)',
        'es': 'Spanish',
        'ru': 'Russian',
        'ko': 'Korean',
        'vi': 'Vietnamese',
    }
    _PROTECTED_TOKEN_PATTERNS = (
        ('percent', re.compile(
            r'%[A-Za-z_][A-Za-z0-9_]+'
            r'|%(?:\([^)]+\))?[-+#0]*\d*(?:\.\d+)?[A-Za-z%]'
        )),
        ('brace', re.compile(
            r'(?<!\{)\{(?:'
            r'(?:[A-Za-z_][A-Za-z0-9_.\[\]-]*|\d*)'
            r'(?:![rsa])?(?::[^{}\n]+)?'
            r'|%[^{}\n]+%'
            r')\}(?!\})'
        )),
        ('escaped_brace', re.compile(r'\{\{\s*[A-Za-z0-9_.-]*\s*\}\}')),
        ('dollar', re.compile(r'\$\{[^{}\n]+\}|\$[A-Z_][A-Z0-9_]*')),
        ('html', re.compile(r'</?[A-Za-z][^<>]*?>')),
        ('url', re.compile(r'https?://[^\s<>"\']+')),
    )

    def __init__(self, dir_path, oai_trans_instance):
        self.oai_trans = oai_trans_instance
        self._dir = dir_path
        self.dir_name = os.path.basename(self._dir)
        self.bulk_size = self._get_positive_int_setting(
            'I18N_TRANSLATE_BULK_SIZE', self.bulk_size
        )
        self.max_concurrency = self._get_positive_int_setting(
            'I18N_TRANSLATE_CONCURRENCY', self.max_concurrency
        )
        self.max_attempts = self._get_positive_int_setting(
            'I18N_TRANSLATE_MAX_ATTEMPTS', self.max_attempts
        )
        self.request_timeout = self._get_positive_float_setting(
            'I18N_TRANSLATE_TIMEOUT', self.request_timeout
        )
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    @staticmethod
    def _get_positive_int_setting(name, default):
        value = int(os.getenv(name, default))
        if value <= 0:
            raise ValueError(f'{name} must be greater than zero')
        return value

    @staticmethod
    def _get_positive_float_setting(name, default):
        value = float(os.getenv(name, default))
        if value <= 0:
            raise ValueError(f'{name} must be greater than zero')
        return value

    @staticmethod
    def split_dict_into_chunks(input_dict, chunk_size=20):
        if chunk_size <= 0:
            raise ValueError('chunk_size must be greater than zero')
        items = list(input_dict.items())
        return [
            dict(items[index:index + chunk_size])
            for index in range(0, len(items), chunk_size)
        ]

    @classmethod
    def _get_protected_tokens(cls, text):
        tokens = []
        for token_type, pattern in cls._PROTECTED_TOKEN_PATTERNS:
            tokens.extend(
                f'{token_type}:{match.group(0)}'
                for match in pattern.finditer(text)
            )
        return Counter(tokens)

    @classmethod
    def _validate_translation(cls, source, translated):
        if not isinstance(translated, str) or not translated.strip():
            return 'translation is empty'
        if source.count('\n') != translated.count('\n'):
            return 'line break count changed'

        source_tokens = cls._get_protected_tokens(source)
        translated_tokens = cls._get_protected_tokens(translated)
        if source_tokens != translated_tokens:
            missing = list((source_tokens - translated_tokens).elements())
            unexpected = list((translated_tokens - source_tokens).elements())
            return f'protected tokens changed (missing={missing}, unexpected={unexpected})'
        return None

    @staticmethod
    def _parse_translation_response(response, expected_count):
        if not response or not response.strip():
            raise ValueError('translator returned an empty response')

        payload = response.strip()
        if payload.startswith('```'):
            lines = payload.splitlines()
            lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines.pop()
            payload = '\n'.join(lines).strip()

        try:
            translations = json.loads(payload)
        except json.JSONDecodeError as error:
            raise ValueError('translator did not return a valid JSON array') from error

        if not isinstance(translations, list):
            raise ValueError('translator response must be a JSON array')
        if len(translations) != expected_count:
            raise ValueError(
                f'translator returned {len(translations)} items, expected {expected_count}'
            )
        if not all(isinstance(item, str) for item in translations):
            raise ValueError('all translated items must be strings')
        return translations

    async def _request_translations(self, values, target_lang):
        payload = json.dumps(values, ensure_ascii=False)
        async with self._semaphore:
            response = await asyncio.wait_for(
                self.oai_trans.translate_text(payload, target_lang),
                timeout=self.request_timeout,
            )
        return self._parse_translation_response(response, len(values))

    async def create_translate_task(self, data, target_lang):
        translated = {}
        pending = dict(data)
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            items = list(pending.items())
            try:
                translations = await self._request_translations(
                    [source for _, source in items], target_lang
                )
            except Exception as error:
                last_error = str(error)
            else:
                retry_items = {}
                validation_errors = []
                for (key, source), result in zip(items, translations):
                    error = self._validate_translation(source, result)
                    if error:
                        retry_items[key] = source
                        validation_errors.append(f'{key!r}: {error}')
                        continue
                    translated[key] = result
                pending = retry_items
                if not pending:
                    return translated
                last_error = '; '.join(validation_errors[:3])

            if attempt < self.max_attempts:
                delay = self.retry_delay * (2 ** (attempt - 1))
                print(
                    f'{YELLOW}{target_lang} batch attempt {attempt} failed: '
                    f'{last_error}; retrying in {delay}s{RESET}'
                )
                await asyncio.sleep(delay)

        failed_keys = ', '.join(repr(key) for key in list(pending)[:5])
        raise TranslationError(
            f'{target_lang} translation failed after {self.max_attempts} attempts '
            f'for {failed_keys}: {last_error}'
        )

    async def bulk_translate(self, need_trans_dict, target_lang):
        if not need_trans_dict:
            return {}
        split_data = self.split_dict_into_chunks(need_trans_dict, self.bulk_size)
        number_of_tasks = len(split_data)
        bar_format = "{l_bar}%s{bar}%s{r_bar}" % (GREEN, RESET)
        desc = f"{target_lang} translate"

        async def translate_batch(batch, progress_bar):
            try:
                return await self.create_translate_task(batch, target_lang)
            finally:
                progress_bar.update(1)

        with tqdm(
                total=number_of_tasks, ncols=100,
                desc=desc, bar_format=bar_format,
                disable=not sys.stderr.isatty(),
        ) as pbar:
            tasks = [translate_batch(batch, pbar) for batch in split_data]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        translated_dict = {}
        errors = []
        for result in results:
            if isinstance(result, BaseException):
                if isinstance(result, asyncio.CancelledError):
                    raise result
                errors.append(result)
            else:
                translated_dict.update(result)

        if errors:
            details = '; '.join(str(error) for error in errors[:3])
            raise TranslationError(
                f'{len(errors)} of {number_of_tasks} {target_lang} batches failed: {details}'
            )

        return {
            key: translated_dict[key]
            for key in need_trans_dict
            if key in translated_dict
        }
