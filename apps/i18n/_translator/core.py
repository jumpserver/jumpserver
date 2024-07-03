import os

import polib

from .base import BaseTranslateManager
from .const import RED, GREEN, MAGENTA


class CoreTranslateManager(BaseTranslateManager):

    @staticmethod
    def get_need_trans_dict(zh_dict, trans_po):
        need_trans_dict = {
            entry.msgid: zh_dict[entry.msgid]
            for entry in trans_po.untranslated_entries() + trans_po.fuzzy_entries()
            if entry.msgid in zh_dict
        }
        return need_trans_dict

    @staticmethod
    def save_translations_to_po(data, trans_po):
        try:
            for entry in trans_po.untranslated_entries() + trans_po.fuzzy_entries():
                if entry.msgid not in data:
                    print(f'{MAGENTA}msgid: {entry.msgid} not in data.{MAGENTA}')
                    continue
                entry.flags = []
                entry.previous_msgid = None
                entry.msgstr = data[entry.msgid]
            trans_po.save()
        except Exception as e:
            print(f'{RED}File save error: {e}{RED}')

    async def run(self):
        po_file_path = os.path.join(self._dir, 'zh', 'LC_MESSAGES', 'django.po')
        po = polib.pofile(po_file_path)
        zh_dict = {entry.msgid: entry.msgstr for entry in po.translated_entries()}

        for file_prefix, target_lang in self.LANG_MAPPER.items():
            file_prefix = 'zh_Hant' if file_prefix == 'zh_hant' else file_prefix
            po_file_path = os.path.join(self._dir, file_prefix, 'LC_MESSAGES', 'django.po')
            trans_po = polib.pofile(po_file_path)
            need_trans_dict = self.get_need_trans_dict(zh_dict, trans_po)
            print(f'{GREEN}Translate: {self.dir_name} {file_prefix} '
                  f'django.po need to translate {len(need_trans_dict)}{GREEN}\n')
            if not need_trans_dict:
                continue
            translated_dict = await self.bulk_translate(need_trans_dict, target_lang)
            self.save_translations_to_po(translated_dict, trans_po)
