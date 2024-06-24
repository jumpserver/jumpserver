#!/usr/bin/env python
#

import json
import os


def sort_json(json_file):
    with open(json_file, 'r') as f:
        json_data = json.load(f)

    with open(json_file, 'w') as f:
        json.dump(json_data, f, indent=4, sort_keys=True, ensure_ascii=False)


def walk_dir(dir_path):
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.json'):
                sort_json(os.path.join(root, file))


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    walk_dir(base_dir)
