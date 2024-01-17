import asyncio
import os

from _translator.const import LOCALE_DIR, RED
from _translator.core import CoreTranslateManager
from _translator.other import OtherTranslateManager
from _translator.utils import OpenAITranslate


class Translate:
    IGNORE_TRANSLATE_DIRS = ('translate',)

    def __init__(self, oai_trans_instance):
        self.oai_trans = oai_trans_instance

    def get_dir_names(self):
        dir_names = []
        for name in os.listdir(LOCALE_DIR):
            _path = os.path.join(LOCALE_DIR, name)
            if not os.path.isdir(_path) or name in self.IGNORE_TRANSLATE_DIRS:
                continue
            dir_names.append(name)
        return dir_names

    async def core_trans(self, dir_name):
        return
        _dir = os.path.join(LOCALE_DIR, dir_name)
        zh_file = os.path.join(_dir, 'zh', 'LC_MESSAGES', 'django.po')
        if not os.path.exists(zh_file):
            print(f'{RED}File: {zh_file} not exists.{RED}')
            return

        await CoreTranslateManager(_dir, self.oai_trans).run()

    async def other_trans(self, dir_name):
        _dir = os.path.join(LOCALE_DIR, dir_name)
        zh_file = os.path.join(_dir, 'zh.json')
        if not os.path.exists(zh_file):
            print(f'{RED}File: {zh_file} not exists.{RED}\n')
            return

        await OtherTranslateManager(_dir, self.oai_trans).run()

    async def run(self):
        dir_names = self.get_dir_names()
        if not dir_names:
            return

        for dir_name in dir_names:
            if dir_name.startswith('_'):
                continue
            if hasattr(self, f'{dir_name}_trans'):
                await getattr(self, f'{dir_name}_trans')(dir_name)
            else:
                await self.other_trans(dir_name)


if __name__ == '__main__':
    oai_trans = OpenAITranslate()
    manager = Translate(oai_trans)
    asyncio.run(manager.run())
