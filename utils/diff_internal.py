import difflib
import json
import sys


def diff_list(f1, f2):
    with open(f1) as f:
        data1 = json.load(f)

    data1_mapper = {
        d['name']: d for d in data1
    }
    with open(f2) as f:
        data2 = json.load(f)

    data2_mapper = {
        d['name']: d for d in data2
    }

    d1_names = set(data1_mapper.keys())
    d2_names = set(data2_mapper.keys())

    diff_names = d1_names - d2_names
    if diff_names:
        print("Diff Names1: ", diff_names)

    diff_names = d2_names - d1_names
    if diff_names:
        print("Diff Names2: ", diff_names)

    for name, data in data1_mapper.items():
        if name not in data2_mapper:
            continue
        data2 = data2_mapper[name]
        print("Diff: ", name)
        diff = difflib.unified_diff(
            json.dumps(data, indent=4, sort_keys=True).splitlines(),
            json.dumps(data2, indent=4, sort_keys=True).splitlines()
        )
        print('\n'.join(diff))
        print()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python diff.py file1 file2')
        sys.exit(1)

    f1 = sys.argv[1]
    f2 = sys.argv[2]

    diff = diff_list(f1, f2)
