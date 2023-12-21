import io

import yaml
from django.conf import settings
from jinja2 import Environment


def translate(key, i18n, lang):
    lang = settings.LANGUAGE_CODE if lang is None else lang
    lang = lang[:2]
    lang_data = i18n.get(key, {})
    return lang_data.get(lang, key)


def yaml_load_with_i18n(stream, lang=None):
    ori_text = stream.read()
    stream = io.StringIO(ori_text)
    yaml_data = yaml.safe_load(stream)
    i18n = yaml_data.get('i18n', {})

    env = Environment()
    env.filters['trans'] = lambda key: translate(key, i18n, lang)
    template = env.from_string(ori_text)
    yaml_data = template.render()
    yaml_f = io.StringIO(yaml_data)
    d = yaml.safe_load(yaml_f)
    if isinstance(d, dict):
        d.pop('i18n', None)
    return d


if __name__ == '__main__':
    with open('manifest.yml') as f:
        data = yaml_load_with_i18n(f)
        print(data)
