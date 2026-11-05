#!/usr/bin/env python3
"""Check migration numbers without importing Django or connecting to a database."""
import argparse
import sys
from pathlib import Path


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps'))
    from common.migration_checks import check_migration_numbers

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apps_dir', nargs='?', type=Path, default=Path(__file__).resolve().parents[1] / 'apps')
    apps_dir = parser.parse_args().apps_dir.resolve()
    if not apps_dir.is_dir():
        parser.error(f'App directory does not exist: {apps_dir}')
    try:
        check_migration_numbers(apps_dir)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    except (OSError, SyntaxError, UnicodeError) as error:
        print(f'Cannot inspect migrations: {error}', file=sys.stderr)
        return 1
    print('No duplicate migration numbers found.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
