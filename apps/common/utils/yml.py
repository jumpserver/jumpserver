import io

import yaml
from django.utils.translation import get_language
from jinja2 import Environment


def translate(i18n, key):
    lang = get_language()[:2]
    lang_data = i18n.get(lang, {})
    return lang_data.get(key, key)


def yaml_load_with_i18n(stream):
    ori_text = stream.read()
    stream = io.StringIO(ori_text)
    yaml_data = yaml.safe_load(stream)
    i18n = yaml_data.get('i18n', {})

    env = Environment()
    env.filters['trans'] = lambda key: translate(i18n, key)
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
