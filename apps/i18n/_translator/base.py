import asyncio
import os

from tqdm import tqdm

from .const import RED, GREEN, RESET


class BaseTranslateManager:
    bulk_size = 15
    SEPARATOR = "<SEP>"
    LANG_MAPPER = {
        'ja': 'Japanese',
        'zh_hant': 'Taiwan',
        # 'en': 'English',
    }

    def __init__(self, dir_path, oai_trans_instance):
        self.oai_trans = oai_trans_instance
        self._dir = dir_path
        self.dir_name = os.path.basename(self._dir)
        if not os.path.exists(self._dir):
            os.makedirs(self._dir)

    @staticmethod
    def split_dict_into_chunks(input_dict, chunk_size=20):
        temp = {}
        result = []

        for i, (k, v) in enumerate(input_dict.items()):
            temp[k] = v
            if (i + 1) % chunk_size == 0 or i == len(input_dict) - 1:
                result.append(temp)
                temp = {}

        return result

    async def create_translate_task(self, data, target_lang):
        try:
            keys = list(data.keys())
            values = list(data.values())
            combined_text = self.SEPARATOR.join(values)
            translated_text = await self.oai_trans.translate_text(combined_text, target_lang)
            translated_texts = translated_text.split(self.SEPARATOR)
            return dict(zip(keys, translated_texts))
        except Exception as e:
            print(f"{RED}Error during translation task: {e}{RED}")
            return {}

    async def bulk_translate(self, need_trans_dict, target_lang):
        split_data = self.split_dict_into_chunks(need_trans_dict, self.bulk_size)

        tasks = [self.create_translate_task(batch, target_lang) for batch in split_data]
        number_of_tasks = len(tasks)
        translated_dict = {}
        bar_format = "{l_bar}%s{bar}%s{r_bar}" % (GREEN, RESET)
        desc = f"{target_lang} translate"
        with tqdm(
                total=number_of_tasks, ncols=100,
                desc=desc, bar_format=bar_format
        ) as pbar:
            for task in asyncio.as_completed(tasks):
                pbar.set_description_str(f"{GREEN}{desc}{RESET}")
                result = await task
                translated_dict.update(result)
                pbar.update(1)

        return translated_dict
