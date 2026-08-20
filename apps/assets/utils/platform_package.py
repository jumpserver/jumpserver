import os
import re


def is_ignored_pkg_path(path):
    parts = os.path.normpath(path).split(os.sep)
    for part in parts:
        if not part:
            continue
        if part == '__MACOSX' or part.startswith('._'):
            return True
    return False


def locate_package_root(extract_to, filename, required_file):
    candidates = []
    if os.path.exists(os.path.join(extract_to, required_file)):
        candidates.append(extract_to)

    expected_name, _ = os.path.splitext(filename)
    expected = os.path.join(extract_to, expected_name)
    if os.path.exists(expected):
        candidates.append(expected)

    matched = re.match(r"(\w+)", filename)
    if matched:
        expected_by_name = os.path.join(extract_to, matched.group())
        if os.path.exists(expected_by_name):
            candidates.append(expected_by_name)

    for item in os.listdir(extract_to):
        if is_ignored_pkg_path(item):
            continue
        path = os.path.join(extract_to, item)
        if not os.path.isdir(path):
            continue
        if os.path.exists(os.path.join(path, required_file)):
            candidates.append(path)

    unique_candidates = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)

    if len(unique_candidates) == 1:
        return unique_candidates[0]
    if unique_candidates:
        return unique_candidates[0]
    return expected
