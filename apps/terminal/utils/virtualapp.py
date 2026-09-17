import errno
import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
import time
from compression import zstd
from contextlib import ExitStack
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError

from common.utils import get_logger
from terminal.models import VirtualApp


MAX_IMAGE_SIZE = 10 * 1024 ** 3
MAX_SCAN_SIZE = 64 * 1024 ** 3
MAX_SCAN_SECONDS = 180
MAX_METADATA_SIZE = 2 * 1024 ** 2
logger = get_logger(__name__)


def archive_root(app):
    return Path(settings.DATA_DIR) / 'virtualapp' / 'images' / str(app.pk)


def _image_reference(value):
    if not isinstance(value, str) or not value:
        return ''
    parts = value.split('/')
    if len(parts) == 1 or not ('.' in parts[0] or ':' in parts[0] or parts[0] == 'localhost'):
        parts.insert(0, 'docker.io')
    if parts[0] == 'index.docker.io':
        parts[0] = 'docker.io'
    if parts[0] == 'docker.io' and len(parts) == 2:
        parts.insert(1, 'library')
    if ':' not in parts[-1] and '@' not in parts[-1]:
        parts[-1] += ':latest'
    return '/'.join(parts)


def _member_name(name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or '..' in path.parts or '\\' in name:
        raise ValidationError('Unsafe path in application image archive')
    return str(path)


class _ArchiveReader:
    def __init__(self, source):
        self.source = source
        self.size = 0
        self.started = time.monotonic()

    def read(self, size):
        if size < 0:
            raise ValidationError('Invalid application image archive read size')
        if time.monotonic() - self.started > MAX_SCAN_SECONDS:
            raise ValidationError('Application image archive validation timed out')
        data = self.source.read(min(size, 1024 ** 2))
        self.size += len(data)
        if self.size > MAX_SCAN_SIZE:
            raise ValidationError('Application image archive exceeds the unpacked size limit')
        return data


class _ImageTarInfo(tarfile.TarInfo):
    def _proc_member(self, archive):
        if self.size < 0 or self.type == tarfile.GNUTYPE_SPARSE:
            raise ValidationError('Invalid or sparse entry in application image archive')
        return super()._proc_member(archive)

    def _proc_gnusparse_10(self, next, pax_headers, archive):
        raise ValidationError('Sparse entries are not supported in application image archives')

    def _proc_pax(self, archive):
        self._check_metadata_size(archive)
        return super()._proc_pax(archive)

    def _proc_gnulong(self, archive):
        self._check_metadata_size(archive)
        return super()._proc_gnulong(archive)

    def _check_metadata_size(self, archive):
        size = getattr(archive, '_image_metadata_size', 0) + self.size
        if self.size > MAX_METADATA_SIZE or size > MAX_METADATA_SIZE * 8:
            raise ValidationError('Application image archive has oversized tar metadata')
        archive._image_metadata_size = size


def _json_object(pairs):
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError('Duplicate JSON key')
    return value


def _inspect_archive(path, image_name, compressed):
    manifest, configs, members, descriptors = None, {}, {}, {}
    try:
        source = zstd.open(path, options={zstd.DecompressionParameter.window_log_max: 27}) if compressed else open(path, 'rb')
        with source:
            reader = _ArchiveReader(source)
            with tarfile.open(fileobj=reader, mode='r|', tarinfo=_ImageTarInfo, stream=True) as archive:
                for member in archive:
                    name = _member_name(member.name)
                    if name in members or len(members) >= 10000:
                        raise ValidationError('Duplicate or too many entries in application image archive')
                    if member.size < 0 or not (member.isfile() or member.isdir()) or member.issparse():
                        raise ValidationError('Application image archive contains an unsupported entry')
                    members[name] = member.isfile()
                    if not member.isfile():
                        continue
                    metadata = name == 'manifest.json' or name.endswith('.json') or name.startswith('blobs/sha256/')
                    if not metadata or member.size > MAX_METADATA_SIZE:
                        continue
                    raw = archive.extractfile(member).read()
                    try:
                        value = json.loads(raw, object_pairs_hook=_json_object)
                    except (ValueError, UnicodeDecodeError):
                        if name == 'manifest.json':
                            raise ValidationError('Invalid Docker image manifest')
                        continue
                    if name == 'manifest.json':
                        manifest = value
                    elif isinstance(value, dict) and 'architecture' in value and 'os' in value:
                        if len(configs) >= 16:
                            raise ValidationError('Too many image configurations in application image archive')
                        configs[name] = ({key: value[key] for key in ('os', 'architecture')}, hashlib.sha256(raw).hexdigest())
                    elif (
                        isinstance(value, dict) and value.get('schemaVersion') == 2
                        and isinstance(value.get('config'), dict) and isinstance(value.get('layers'), list)
                        and name.startswith('blobs/sha256/')
                    ):
                        digest = hashlib.sha256(raw).hexdigest()
                        if name != 'blobs/sha256/' + digest or len(descriptors) >= 16:
                            raise ValidationError('Invalid or too many OCI manifests in application image archive')
                        descriptors['sha256:' + digest] = value
            while reader.read(1024 ** 2):
                pass
    except (OSError, EOFError, RecursionError, tarfile.TarError, zstd.ZstdError) as exc:
        raise ValidationError('Invalid application image archive') from exc
    if not isinstance(manifest, list) or len(manifest) != 1 or not isinstance(manifest[0], dict):
        raise ValidationError('Upload a Docker save archive containing one application image')
    entry = manifest[0]
    tags = entry.get('RepoTags')
    if not isinstance(tags, list) or _image_reference(image_name) not in [_image_reference(tag) for tag in tags]:
        raise ValidationError('Application image archive does not contain the configured image name and tag')
    config_name = entry.get('Config')
    if not isinstance(config_name, str) or _member_name(config_name) not in configs:
        raise ValidationError('Application image archive has no valid image configuration')
    config, config_id = configs[_member_name(config_name)]
    layers = entry.get('Layers')
    if not isinstance(layers, list) or any(
        not isinstance(layer, str) or not members.get(_member_name(layer)) for layer in layers
    ):
        raise ValidationError('Application image archive is missing image layers')
    architecture = config.get('architecture')
    if config.get('os') != 'linux' or not isinstance(architecture, str) or not re.fullmatch(r'[a-z0-9_]+', architecture):
        raise ValidationError('Application image archive must contain one Linux platform')
    config_id = 'sha256:' + config_id
    # Config and matching manifest IDs allow local reuse. Other IDs trigger a load.
    manifest_ids = set()
    for digest, descriptor in descriptors.items():
        config_ref, layer_refs = descriptor['config'], descriptor['layers']
        if config_ref.get('digest') != config_id:
            continue
        if not all(
            isinstance(layer, dict) and isinstance(layer.get('digest'), str) for layer in layer_refs
        ):
            continue
        if ['blobs/' + layer['digest'].replace(':', '/') for layer in layer_refs] == layers:
            manifest_ids.add(digest)
    return {
        'os': 'linux', 'architecture': architecture,
        'image_ids': [config_id, *sorted(manifest_ids)],
    }


def _read_manifest(app):
    try:
        path = archive_root(app) / 'manifest.json'
        with path.open('rb') as stream:
            raw = stream.read(MAX_METADATA_SIZE + 1)
        if len(raw) > MAX_METADATA_SIZE:
            raise ValueError
        manifest = json.loads(raw, object_pairs_hook=_json_object)
        if not isinstance(manifest, dict):
            raise ValueError
        for architecture, image in manifest.items():
            if not isinstance(image, dict) or image.get('architecture') != architecture:
                raise ValueError
            for key in ('filename', 'version', 'image_name', 'os', 'architecture', 'sha256', 'file'):
                if not isinstance(image.get(key), str) or not image[key]:
                    raise ValueError
            if (
                image['file'] != Path(image['file']).name or image['file'] in ('.', '..')
                or not re.fullmatch(r'[a-f0-9]{64}', image['sha256'])
                or not isinstance(image.get('size'), int) or not 0 < image['size'] <= MAX_IMAGE_SIZE
            ):
                raise ValueError
            image_ids = image.get('image_ids')
            if (
                not isinstance(image_ids, list) or not 1 <= len(image_ids) <= 17
                or any(not isinstance(value, str) or not re.fullmatch(r'sha256:[a-f0-9]{64}', value) for value in image_ids)
            ):
                raise ValueError
        return manifest
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, RecursionError, UnicodeDecodeError) as exc:
        raise ValidationError('Invalid application image archive metadata') from exc


def get_image_archives(app):
    return list(_read_manifest(app).values())


def _write_manifest(app, images):
    root = archive_root(app)
    descriptor, temporary = tempfile.mkstemp(dir=root, prefix='.manifest-')
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(images, stream)
        os.replace(temporary, root / 'manifest.json')
    finally:
        Path(temporary).unlink(missing_ok=True)


def _remove_archives(app, old, new):
    retained = {image['file'] for image in new.values()}
    for image in old.values():
        if image['file'] not in retained:
            try:
                (archive_root(app) / image['file']).unlink(missing_ok=True)
            except OSError:
                logger.warning('Unable to remove old application image archive: %s', image['file'])


def _check_current_app(app):
    try:
        current = VirtualApp.objects.select_for_update().get(pk=app.pk)
    except VirtualApp.DoesNotExist as exc:
        raise ValidationError('Virtual application no longer exists') from exc
    if (current.version, current.image_name) != (app.version, app.image_name):
        raise ValidationError('Virtual application changed; upload or publish its current image again')


def save_image_archive(app, uploaded_file):
    filename = uploaded_file.name
    compressed = filename.lower().endswith('.zst')
    if not (compressed or filename.lower().endswith('.tar')):
        raise ValidationError('Upload a Docker save image as .tar, .tar.zst or .zst')
    if not 0 < uploaded_file.size <= MAX_IMAGE_SIZE:
        raise ValidationError('Application image archive must be no larger than 10 GiB')
    root = archive_root(app)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(dir=root, prefix='.upload-')
    destination, old = None, {}
    published = False
    try:
        checksum, size = hashlib.sha256(), 0
        with os.fdopen(descriptor, 'wb') as stream:
            for chunk in uploaded_file.chunks():
                size += len(chunk)
                if size > MAX_IMAGE_SIZE:
                    raise ValidationError('Application image archive must be no larger than 10 GiB')
                stream.write(chunk)
                checksum.update(chunk)
        image = _inspect_archive(temporary, app.image_name, compressed)
        image.update(filename=filename, size=size, version=app.version, image_name=app.image_name,
                     sha256=checksum.hexdigest())
        image['file'] = f"{image['architecture']}-{image['sha256']}.tar" + ('.zst' if compressed else '')
        with transaction.atomic():
            _check_current_app(app)
            old = _read_manifest(app)
            images = {key: value for key, value in old.items()
                      if (value['version'], value['image_name']) == (app.version, app.image_name)}
            images[image['architecture']] = image
            destination = root / image['file']
            os.replace(temporary, destination)
            _write_manifest(app, images)
            published = True
            _remove_archives(app, old, images)
        return image
    finally:
        Path(temporary).unlink(missing_ok=True)
        if destination and not published and destination.name not in {item['file'] for item in old.values()}:
            destination.unlink(missing_ok=True)


def delete_image_archive(app, architecture):
    with transaction.atomic():
        _check_current_app(app)
        images = _read_manifest(app)
        if architecture not in images:
            raise ValidationError('No application image archive for this architecture')
        old = dict(images)
        images.pop(architecture)
        _write_manifest(app, images)
        _remove_archives(app, old, images)


def stage_image_archives(app, run_dir):
    resources = {}
    with ExitStack() as stack:
        copies = []
        with transaction.atomic():
            _check_current_app(app)
            for architecture, image in _read_manifest(app).items():
                if (image['version'], image['image_name']) != (app.version, app.image_name):
                    continue
                source = archive_root(app) / image['file']
                destination = Path(run_dir).resolve() / 'offline' / source.name
                try:
                    if source.is_symlink() or (source.exists() and not source.is_file()):
                        raise ValidationError('Invalid offline application image archive path')
                    if not source.exists():
                        continue
                    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    try:
                        os.link(source, destination)
                    except OSError as exc:
                        if exc.errno != errno.EXDEV:
                            raise
                        # Keep the open inode if an upload replaces the archive.
                        copies.append((stack.enter_context(source.open('rb')), destination))
                except FileNotFoundError:
                    if not source.exists():
                        continue
                    raise
                except OSError as exc:
                    raise ValidationError('Offline application image cannot be staged; upload it again') from exc
                resources[architecture] = {**image, 'file': str(destination)}
        for source, destination in copies:
            with destination.open('wb') as output:
                shutil.copyfileobj(source, output, 1024 ** 2)
    return resources
