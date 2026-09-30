import re

from terminal import const


def parse_tinker_version(value):
    if not isinstance(value, str):
        return None
    # Only released versions with three numeric components are supported.
    match = re.fullmatch(r'[vV]?([0-9]+)\.([0-9]+)\.([0-9]+)', value.strip())
    return tuple(map(int, match.groups())) if match else None


def get_tinker_version_status(value):
    version = parse_tinker_version(value)
    if version is None:
        return 'unknown'
    if version < parse_tinker_version(const.TINKER_MIN_VERSION):
        return 'unsupported'
    target = parse_tinker_version(const.TINKER_TARGET_VERSION)
    if version < target:
        return 'compatible'
    if version > target:
        return 'newer'
    return 'ok'
