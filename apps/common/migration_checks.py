"""Database-free migration-number validation shared by startup and CI."""
import ast
import re
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


def check_migration_numbers(apps_dir):
    apps_dir = Path(apps_dir).resolve()
    if not apps_dir.is_dir():
        raise ValueError(f'App directory does not exist: {apps_dir}')
    migrations = defaultdict(list)
    for path in sorted(apps_dir.rglob('migrations/*.py')):
        match = re.match(r'([0-9]+)_', path.name)
        if match and not is_squashed(path):
            migrations[(path.parent, int(match[1]))].append(path.name)
    duplicates = {key: names for key, names in migrations.items() if len(names) > 1}
    if duplicates:
        lines = ['Duplicate migration numbers found:']
        for (directory, number), names in sorted(duplicates.items()):
            lines.append(f'  {directory.relative_to(apps_dir.parent)}: {number:04d}')
            lines.extend(f'    {name}' for name in names)
        raise ValueError('\n'.join(lines))
