import json
import os
import tempfile

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


INVENTORY_LITERAL_PATHS = (
    ("all", "hosts", "*", "ansible_host"),
    ("all", "hosts", "*", "jms_asset", "address"),
    ("all", "hosts", "*", "jms_asset", "origin_address"),
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


def sanitize_inventory_by_paths(value, path_patterns, current_path=()):
    # 递归遍历 inventory，只在命中高风险路径时处理对应值
    if isinstance(value, dict):
        return {
            key: sanitize_inventory_by_paths(item, path_patterns, current_path + (key,))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            sanitize_inventory_by_paths(item, path_patterns, current_path + (str(index),))
            for index, item in enumerate(value)
        ]
    if isinstance(value, tuple):
        return tuple(
            sanitize_inventory_by_paths(item, path_patterns, current_path + (str(index),))
            for index, item in enumerate(value)
        )

    if any(path_matches_pattern(current_path, pattern) for pattern in path_patterns):
        return sanitize_ansible_inventory_value(value)
    return value


def path_matches_pattern(path, pattern):
    # `*` 只匹配单层，例如 host 名
    if len(path) != len(pattern):
        return False
    return all(expected == "*" or actual == expected for actual, expected in zip(path, pattern))


def atomic_dump_text(dest_path, writer):
    # 先写临时文件，再原子替换，避免目标文件出现半写入状态
    dest_dir = os.path.dirname(dest_path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dest_dir)
    try:
        with os.fdopen(fd, "w") as f:
            writer(f)
        os.replace(tmp_path, dest_path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def sanitize_ansible_playbook(playbook_path, dest_path):
    with open(playbook_path) as f:
        plays = yaml.safe_load(f)

    for play in plays or []:
        vars_data = play.get("vars")
        if isinstance(vars_data, dict):
            play["vars"] = wrap_ansible_unsafe(vars_data)

    atomic_dump_text(dest_path, lambda f: dump_ansible_yaml(plays, f))


def sanitize_ansible_inventory_json(inventory_path, dest_path):
    with open(inventory_path) as f:
        data = json.load(f)

    data = sanitize_inventory_by_paths(data, INVENTORY_LITERAL_PATHS)

    atomic_dump_text(dest_path, lambda f: json.dump(data, f, indent=4))


if __name__ == '__main__':
    with open('manifest.yml') as f:
        data = yaml_load_with_i18n(f)
        print(data)
