import os

import polib

from .base import BaseTranslateManager


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
                    print(f'msgid: {entry.msgid} not in data.')
                    continue
                entry.flags = []
                entry.previous_msgid = None
                entry.msgstr = data[entry.msgid]
            trans_po.save()
        except Exception as e:
            print(f'File save error: {e}')

    async def run(self):
        po_file_path = os.path.join(self._dir, 'zh', 'LC_MESSAGES', 'django.po')
        po = polib.pofile(po_file_path)
        zh_dict = {entry.msgid: entry.msgstr for entry in po.translated_entries()}

        for file_prefix, target_lang in self.LANG_MAPPER.items():
            po_file_path = os.path.join(self._dir, file_prefix, 'LC_MESSAGES', 'django.po')
            trans_po = polib.pofile(po_file_path)
            need_trans_dict = self.get_need_trans_dict(zh_dict, trans_po)
            print(f'File: {file_prefix}.json need to translate: {len(need_trans_dict)}')
            if not need_trans_dict:
                print(f'File: {file_prefix}.json is already translated.')
                continue
            translated_dict = await self.bulk_translate(need_trans_dict, target_lang)
            self.save_translations_to_po(translated_dict, trans_po)
