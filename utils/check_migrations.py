#!/usr/bin/env python3
"""Check migration numbers without importing Django or connecting to a database."""
import argparse
import ast
import re
import sys
import tokenize
from collections import defaultdict
from pathlib import Path


def is_squashed(path):
    with tokenize.open(path) as source:
        tree = ast.parse(source.read(), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != 'Migration':
            continue
        for statement in node.body:
            targets = statement.targets if isinstance(statement, ast.Assign) else (
                [statement.target] if isinstance(statement, ast.AnnAssign) else []
            )
            if any(isinstance(target, ast.Name) and target.id == 'replaces' for target in targets):
                # ponytail: generated squashes declare a literal replaces list/tuple.
                # If dynamic replacements are introduced, use Django's MigrationLoader.
                return isinstance(statement.value, (ast.List, ast.Tuple)) and bool(statement.value.elts)
    return False


def find_duplicates(apps_dir):
    migrations = defaultdict(list)
    for path in sorted(apps_dir.rglob('migrations/*.py')):
        match = re.match(r'([0-9]+)_', path.name)
        if match and not is_squashed(path):
            migrations[(path.parent, int(match[1]))].append(path.name)
    return {key: names for key, names in migrations.items() if len(names) > 1}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apps_dir', nargs='?', type=Path, default=Path(__file__).resolve().parents[1] / 'apps')
    apps_dir = parser.parse_args().apps_dir.resolve()
    if not apps_dir.is_dir():
        parser.error(f'App directory does not exist: {apps_dir}')
    try:
        duplicates = find_duplicates(apps_dir)
    except (OSError, SyntaxError, UnicodeError) as error:
        print(f'Cannot inspect migrations: {error}', file=sys.stderr)
        return 1
    if not duplicates:
        print('No duplicate migration numbers found.')
        return 0
    print('Duplicate migration numbers found:', file=sys.stderr)
    for (directory, number), names in sorted(duplicates.items()):
        print(f'  {directory.relative_to(apps_dir.parent)}: {number:04d}', file=sys.stderr)
        for name in names:
            print(f'    {name}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
