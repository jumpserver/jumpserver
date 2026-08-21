import os

import polib

from .base import BaseTranslateManager
from .const import GREEN, RESET, YELLOW


class CoreTranslateManager(BaseTranslateManager):

    @staticmethod
    def get_need_trans_dict(zh_dict, trans_po):
        return {
            entry.msgid: zh_dict[entry.msgid]
            for entry in trans_po
            if not entry.obsolete
            and not entry.msgid_plural
            and entry.msgid
            and entry.msgid in zh_dict
            and (not entry.msgstr or 'fuzzy' in entry.flags)
        }

    @staticmethod
    def save_translations_to_po(data, trans_po):
        updated = 0
        for entry in trans_po:
            if not entry.obsolete and entry.msgid in data:
                entry.flags = [flag for flag in entry.flags if flag != 'fuzzy']
                entry.previous_msgid = None
                entry.msgstr = data[entry.msgid]
                updated += 1
        if updated:
            trans_po.save()
        return updated

    async def run(self):
        async def process_po(po_name: str):
            po_file_path = os.path.join(self._dir, 'zh', 'LC_MESSAGES', po_name)
            po = polib.pofile(po_file_path)
            zh_dict = {
                entry.msgid: entry.msgstr
                for entry in po.translated_entries()
                if entry.msgid and entry.msgstr
            }

            for file_prefix, target_lang in self.LANG_MAPPER.items():
                po_file_path = os.path.join(self._dir, file_prefix, 'LC_MESSAGES', po_name)
                if not os.path.exists(po_file_path):
                    print(f'{YELLOW}Skip missing file: {po_file_path}{RESET}')
                    continue
                trans_po = polib.pofile(po_file_path)
                need_trans_dict = self.get_need_trans_dict(zh_dict, trans_po)
                print(f'{GREEN}Translate: {self.dir_name} {file_prefix} '
                      f'{po_name} need to translate {len(need_trans_dict)}{RESET}\n')
                if not need_trans_dict:
                    continue
                translated_dict = await self.bulk_translate(need_trans_dict, target_lang)
                self.save_translations_to_po(translated_dict, trans_po)

        await process_po('django.po')
        djangojs_po = os.path.join(self._dir, 'zh', 'LC_MESSAGES', 'djangojs.po')
        if os.path.exists(djangojs_po):
            await process_po('djangojs.po')
