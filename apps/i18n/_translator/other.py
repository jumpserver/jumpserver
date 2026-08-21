import json
import os

from .base import BaseTranslateManager
from .const import GREEN, RESET


class OtherTranslateManager(BaseTranslateManager):

    @staticmethod
    def get_need_trans_dict(zh_dict, other_dict):
        return {
            key: value
            for key, value in zh_dict.items()
            if key and value and not other_dict.get(key)
        }

    def load_json_as_dict(self, file_prefix='zh'):
        file_path = os.path.join(self._dir, f'{file_prefix}.json')
        if not os.path.exists(file_path):
            return {}
        with open(file_path, 'r', encoding='utf-8') as file_obj:
            data = json.load(file_obj)
        if not isinstance(data, dict):
            raise ValueError(f'File must contain a JSON object: {file_path}')
        invalid_keys = [key for key, value in data.items() if not isinstance(value, str)]
        if invalid_keys:
            raise ValueError(
                f'File contains non-string values: {file_path}: {invalid_keys[:5]}'
            )
        return data

    def save_dict_as_json(self, data, file_prefix='ja'):
        file_path = os.path.join(self._dir, f'{file_prefix}.json')
        temp_path = f'{file_path}.tmp'
        try:
            with open(temp_path, 'w', encoding='utf-8') as file_obj:
                json.dump(data, file_obj, ensure_ascii=False, sort_keys=True, indent=4)
                file_obj.write('\n')
            os.replace(temp_path, file_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def run(self):
        zh_dict = self.load_json_as_dict()

        for file_prefix, target_lang in self.LANG_MAPPER.items():
            file_prefix = file_prefix.lower()
            other_dict = self.load_json_as_dict(file_prefix)
            need_trans_dict = self.get_need_trans_dict(zh_dict, other_dict)
            print(f'{GREEN}Translate: {self.dir_name} {file_prefix} need to translate '
                  f'{len(need_trans_dict)}{RESET}\n')
            if not need_trans_dict:
                continue
            translated_dict = await self.bulk_translate(need_trans_dict, target_lang)
            other_dict.update(translated_dict)
            self.save_dict_as_json(other_dict, file_prefix)
