import json
import os

from .base import BaseTranslateManager
from .const import RED, GREEN


class OtherTranslateManager(BaseTranslateManager):

    @staticmethod
    def get_need_trans_dict(zh_dict, other_dict):
        diff_keys = set(zh_dict.keys()) - set(other_dict.keys())
        need_trans_dict = {k: zh_dict[k] for k in diff_keys if k}
        return need_trans_dict

    def load_json_as_dict(self, file_prefix='zh'):
        file_path = os.path.join(self._dir, f'{file_prefix}.json')
        if not os.path.exists(file_path):
            return {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f'{RED}File: {file_path} load error: {e}{RED}')
            return {}

    def save_dict_as_json(self, data, file_prefix='ja'):
        file_path = os.path.join(self._dir, f'{file_prefix}.json')
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, sort_keys=True, indent=4)
        except Exception as e:
            print(f'{RED}File: {file_path} save error: {e}{RED}')

    async def run(self):
        zh_dict = self.load_json_as_dict()

        for file_prefix, target_lang in self.LANG_MAPPER.items():
            file_prefix = file_prefix.lower()
            other_dict = self.load_json_as_dict(file_prefix)
            need_trans_dict = self.get_need_trans_dict(zh_dict, other_dict)
            print(f'{GREEN}Translate: {self.dir_name} {file_prefix} need to translate '
                  f'{len(need_trans_dict)}{GREEN}\n')
            if not need_trans_dict:
                continue
            translated_dict = await self.bulk_translate(need_trans_dict, target_lang)
            other_dict.update(translated_dict)
            self.save_dict_as_json(other_dict, file_prefix)
