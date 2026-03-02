import yaml
from django.conf import settings
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment


def translate(key, i18n, lang):
    lang = settings.LANGUAGE_CODE if lang is None else lang
    lang = lang[:2]
    lang_data = i18n.get(key, {})
    return lang_data.get(lang, key)


def yaml_load_with_i18n(stream, lang=None):
    ori_text = stream.read()
    data = yaml.safe_load(ori_text)
    i18n = data.get("i18n", {})

    env = SandboxedEnvironment(
        undefined=StrictUndefined,
        autoescape=False,
    )

    def safe_trans(key):
        if not isinstance(key, str):
            raise ValueError("invalid i18n key")
        return translate(key, i18n, lang)

    env.filters.clear()
    env.globals.clear()
    env.filters["trans"] = safe_trans

    template = env.from_string(ori_text)
    try:
        rendered = template.render()
    except Exception as e:
        rendered = ori_text

    result = yaml.safe_load(rendered)
    result.pop("i18n", None)
    return result


if __name__ == '__main__':
    with open('manifest.yml') as f:
        data = yaml_load_with_i18n(f)
        print(data)
