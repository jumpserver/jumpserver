import asyncio
import os


class BaseTranslateManager:
    bulk_size = 30
    SEPARATOR = "<SEP>"
    LANG_MAPPER = {
        # 'ja': 'Japanese',
        'en': 'English',
    }

    def __init__(self, dir_path, oai_trans_instance):
        self.oai_trans = oai_trans_instance
        self._dir = dir_path
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
            print(f"Error during translation task: {e}")
            return {}

    async def bulk_translate(self, need_trans_dict, target_lang):
        split_data = self.split_dict_into_chunks(need_trans_dict, self.bulk_size)

        tasks = [self.create_translate_task(batch, target_lang) for batch in split_data]
        translated_results = await asyncio.gather(*tasks)
        translated_dict = {}
        for result in translated_results:
            translated_dict.update(result)

        return translated_dict
