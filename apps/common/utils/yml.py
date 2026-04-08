import json

import yaml
from ansible.utils.unsafe_proxy import wrap_var
from django.conf import settings
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment


class AnsibleUnsafeDumper(yaml.SafeDumper):
    pass


UnsafeTextType = type(wrap_var(''))
AnsibleUnsafeDumper.add_representer(
    UnsafeTextType,
    lambda dumper, data: dumper.represent_scalar('!unsafe', str(data))
)


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


def wrap_ansible_unsafe(value):
    if value is None:
        return value
    if isinstance(value, dict):
        return {k: wrap_ansible_unsafe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [wrap_ansible_unsafe(v) for v in value]
    if isinstance(value, tuple):
        return tuple(wrap_ansible_unsafe(v) for v in value)
    if isinstance(value, str):
        return wrap_var(value)
    return value


def dump_ansible_yaml(data, stream):
    yaml.dump(
        data,
        stream,
        Dumper=AnsibleUnsafeDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


def escape_ansible_jinja(value):
    if not isinstance(value, str):
        return value

    return (
        value
        .replace('{{', '{{ "{{" }}')
        .replace('}}', '{{ "}}" }}')
        .replace('{%', '{{ "{%" }}')
        .replace('%}', '{{ "%}" }}')
        .replace('{#', '{{ "{#" }}')
        .replace('#}', '{{ "#}" }}')
    )


def sanitize_ansible_inventory_value(value):
    if isinstance(value, dict):
        return {k: sanitize_ansible_inventory_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_ansible_inventory_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(sanitize_ansible_inventory_value(v) for v in value)
    return escape_ansible_jinja(value)


def sanitize_ansible_playbook(playbook_path, dest_path):
    with open(playbook_path) as f:
        plays = yaml.safe_load(f)

    for play in plays or []:
        vars_data = play.get("vars")
        if isinstance(vars_data, dict):
            play["vars"] = wrap_ansible_unsafe(vars_data)

    with open(dest_path, "w") as f:
        dump_ansible_yaml(plays, f)


def sanitize_ansible_inventory_json(inventory_path, dest_path):
    with open(inventory_path) as f:
        data = json.load(f)

    for host_name, host in data.get("all", {}).get("hosts", {}).items():
        data["all"]["hosts"][host_name] = sanitize_ansible_inventory_value(host)

    with open(dest_path, "w") as f:
        json.dump(data, f, indent=4)


if __name__ == '__main__':
    with open('manifest.yml') as f:
        data = yaml_load_with_i18n(f)
        print(data)
