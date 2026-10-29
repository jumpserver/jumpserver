"""Source-only installation bundles from the clients shipped with this Core."""
from io import BytesIO
from pathlib import Path
import tarfile

from django.conf import settings
from rest_framework.exceptions import NotFound


GO_SOURCES = ('go/*.go', 'go/go.mod', 'go/go.sum')
SOURCE_FILES = {
    'socket': ('socket/python_example.py', 'socket/README.*.md'),
    'python': (
        'python/jms_pam/**/*.py', 'python/jms_pam/py.typed',
        'python/setup.py', 'python/pyproject.toml', 'python/README.*.md',
    ),
    'go': GO_SOURCES,
    'java': ('java/src/main/**/*.java', 'java/pom.xml'),
    'node': ('node/index.js', 'node/index.d.ts', 'node/event-dispatcher.js', 'node/event-names.js', 'node/package.json', 'node/package-lock.json'),
    'agent': GO_SOURCES + (
        'agent/cmd/**/*.go', 'agent/internal/**/*.go', 'agent/go.mod', 'agent/go.sum',
    ),
}


def source_archive(language):
    if language not in SOURCE_FILES:
        raise NotFound()
    root = Path(settings.APPS_DIR) / 'accounts' / 'clients'
    files = {}
    for pattern in SOURCE_FILES[language]:
        for path in root.glob(pattern):
            relative = path.relative_to(root)
            if (not path.is_file() or path.is_symlink() or path.name.endswith('_test.go')
                    or any((root / parent).is_symlink() for parent in relative.parents)):
                continue
            files[relative.as_posix()] = path
    if not files:
        raise NotFound()
    output = BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as archive:
        for name, path in sorted(files.items()):
            data = path.read_bytes()
            item = tarfile.TarInfo(f'jms-pam-clients/{name}')
            item.size, item.mode = len(data), 0o644
            archive.addfile(item, BytesIO(data))
    return output.getvalue()
