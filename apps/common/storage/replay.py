import hashlib
import io
import json
import os
import stat
import tarfile
import tempfile
from itertools import chain

from django.core.files.storage import default_storage

from common.utils import make_dirs, get_logger
from terminal.models import Session
from .base import BaseStorageHandler, get_multi_object_storage

logger = get_logger(__name__)


def get_session_preferred_storage_name(session):
    """
    会话所属终端(组件)配置的录像存储名, 录像大概率上传在该存储上, 优先在其中查找
    terminal 可能已被删除 (on_delete=DO_NOTHING), 取不到时返回 None 表示无优先存储
    """
    try:
        terminal = session.terminal
    except Exception:
        return None
    return terminal.replay_storage if terminal else None


class ReplayStorageHandler(BaseStorageHandler):
    NAME = 'REPLAY'

    def get_preferred_storage_name(self):
        return get_session_preferred_storage_name(self.obj)

    def get_file_path(self, **kwargs):
        storage = kwargs['storage']
        # 获取外部存储路径名
        session_path = self.obj.find_ok_relative_path_in_storage(storage)
        if not session_path:
            return None, None

        # 通过外部存储路径名后缀，构造真实的本地存储路径
        return session_path, self.obj.get_local_path_by_relative_path(session_path)

    def find_local(self):
        # 存在外部存储上，所有可能的路径名
        session_paths = self.obj.get_all_possible_relative_path()

        # 存在本地存储上，所有可能的路径名
        local_paths = self.obj.get_all_possible_local_path()

        for _local_path in chain(session_paths, local_paths):
            if default_storage.exists(_local_path):
                url = default_storage.url(_local_path)
                return _local_path, url
        return None, f'{self.NAME} not found.'


class SessionPartReplayStorageHandler(object):
    Name = 'SessionPartReplayStorageHandler'
    INDEX_SCHEMA = 'jumpserver.recording-index'
    INDEX_SCHEMA_VERSION = 1
    INDEX_FILENAME_SUFFIX = '.index.v1.json'
    INDEX_MEDIA_TYPE = 'application/vnd.jumpserver.recording-index+json'

    def __init__(self, obj: Session):
        self.obj = obj

    def find_local_part_file_path(self, part_filename):
        local_path = self.obj.get_replay_part_file_local_storage_path(part_filename)
        if default_storage.exists(local_path):
            url = default_storage.url(local_path)
            return local_path, url
        return None, '{} not found.'.format(part_filename)

    def download_part_file(self, part_filename, validator=None):
        local_path = self.obj.get_replay_part_file_local_storage_path(part_filename)
        remote_path = self.obj.get_replay_part_file_relative_path(part_filename)

        # 保存到storage的路径
        target_path = os.path.join(default_storage.base_location, local_path)
        target_dir = os.path.dirname(target_path)
        if not os.path.isdir(target_dir):
            make_dirs(target_dir, exist_ok=True)
        temporary_fd, target_tmp_path = tempfile.mkstemp(
            prefix='{}.tmp-'.format(os.path.basename(target_path)), dir=target_dir
        )
        os.close(temporary_fd)
        os.remove(target_tmp_path)

        try:
            # 优先只查所属终端配置的存储, 未配置或未命中时回退遍历所有存储
            preferred = get_session_preferred_storage_name(self.obj)
            storage_names = [preferred, None] if preferred else [None]
            ok, err, found_storage = False, None, False
            for name in storage_names:
                storage = get_multi_object_storage(name)
                if not storage:
                    continue
                found_storage = True
                ok, err = storage.download(remote_path, target_tmp_path)
                if ok:
                    break
            if not found_storage:
                msg = "Not found {} file, and not remote storage set".format(part_filename)
                return None, msg
            if not ok:
                msg = 'Failed download {} file: {}'.format(part_filename, err)
                logger.error(msg)
                return None, msg
            if validator:
                validator(target_tmp_path)
            os.replace(target_tmp_path, target_path)
            url = default_storage.url(local_path)
            return local_path, url
        finally:
            if os.path.exists(target_tmp_path):
                os.remove(target_tmp_path)

    def get_part_file_path_url(self, part_filename):
        if (
                not isinstance(part_filename, str)
                or not part_filename
                or part_filename in ('.', '..')
                or os.path.basename(part_filename) != part_filename
                or '/' in part_filename
                or '\\' in part_filename
                or '\x00' in part_filename
        ):
            raise ValueError('invalid replay storage filename: {!r}'.format(part_filename))
        local_path, url = self.find_local_part_file_path(part_filename)
        if local_path is None:
            local_path, url = self.download_part_file(part_filename)
        return local_path, url

    def _expected_index_filename(self):
        return '{}{}'.format(self.obj.id, self.INDEX_FILENAME_SUFFIX)

    def _parse_index_descriptor(self, meta_data):
        if 'index' not in meta_data:
            return None

        descriptor = meta_data['index']
        if not isinstance(descriptor, dict):
            raise ValueError('replay index descriptor must be an object')

        if meta_data.get('type') != 'mp4':
            raise ValueError('replay index is only supported for mp4 manifests')

        schema = descriptor.get('schema')
        if schema != self.INDEX_SCHEMA:
            raise ValueError('unsupported replay index schema: {!r}'.format(schema))

        schema_version = descriptor.get('schema_version')
        if (
                not isinstance(schema_version, int)
                or isinstance(schema_version, bool)
                or schema_version != self.INDEX_SCHEMA_VERSION
        ):
            raise ValueError(
                'unsupported replay index schema_version: {}'.format(schema_version)
            )

        name = descriptor.get('name')
        expected_name = self._expected_index_filename()
        if (
                not isinstance(name, str)
                or name != expected_name
                or os.path.basename(name) != name
                or '/' in name
                or '\\' in name
        ):
            raise ValueError('invalid replay index filename: {!r}'.format(name))

        size = descriptor.get('size')
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ValueError('invalid replay index size: {!r}'.format(size))

        media_type = descriptor.get('media_type')
        if media_type != self.INDEX_MEDIA_TYPE:
            raise ValueError('unsupported replay index media_type: {!r}'.format(media_type))

        checksum = descriptor.get('sha256')
        if (
                not isinstance(checksum, str)
                or len(checksum) != 64
                or any(char not in '0123456789abcdefABCDEF' for char in checksum)
        ):
            raise ValueError('invalid replay index sha256')

        return {
            'schema': schema,
            'schema_version': schema_version,
            'name': name,
            'media_type': media_type,
            'size': size,
            'sha256': checksum.lower(),
        }

    def _parse_part_files(self, meta_data, indexed=False):
        files = meta_data.get('files', [])
        if not isinstance(files, list):
            raise ValueError('replay files must be an array')

        part_files = []
        seen = set()
        for position, part_file in enumerate(files):
            if not isinstance(part_file, dict):
                raise ValueError('replay file {} must be an object'.format(position))
            filename = part_file.get('name')
            if (
                    not isinstance(filename, str)
                    or not filename
                    or filename in ('.', '..')
                    or os.path.basename(filename) != filename
                    or '/' in filename
                    or '\\' in filename
                    or '\x00' in filename
            ):
                raise ValueError(
                    'invalid replay part filename at position {}: {!r}'.format(
                        position, filename
                    )
                )
            if filename.endswith(self.INDEX_FILENAME_SUFFIX):
                raise ValueError(
                    'replay index must use the top-level index descriptor, not files'
                )
            if filename in seen:
                raise ValueError('duplicate replay part filename: {!r}'.format(filename))
            seen.add(filename)
            declared_size = part_file.get('size')
            if indexed:
                if not filename.lower().endswith('.mp4'):
                    raise ValueError(
                        'indexed replay part must be an mp4 file: {!r}'.format(filename)
                    )
                if (
                        not isinstance(declared_size, int)
                        or isinstance(declared_size, bool)
                        or declared_size <= 0
                ):
                    raise ValueError(
                        'invalid indexed replay part size at position {}: {!r}'.format(
                            position, declared_size
                        )
                    )
            part_files.append({'name': filename, 'size': declared_size})
        if indexed and not part_files:
            raise ValueError('indexed replay manifest must contain at least one mp4 part')
        return part_files

    @staticmethod
    def _verify_index_file(index_path, descriptor):
        path_stat = os.lstat(index_path)
        if not stat.S_ISREG(path_stat.st_mode):
            raise ValueError('replay index is not a regular file')

        digest = hashlib.sha256()
        with open(index_path, 'rb') as index_file:
            file_stat = os.fstat(index_file.fileno())
            if (
                    not stat.S_ISREG(file_stat.st_mode)
                    or path_stat.st_dev != file_stat.st_dev
                    or path_stat.st_ino != file_stat.st_ino
            ):
                raise ValueError('replay index file changed while opening')
            for chunk in iter(lambda: index_file.read(1024 * 1024), b''):
                digest.update(chunk)

        if file_stat.st_size != descriptor['size']:
            raise ValueError(
                'replay index size mismatch: declared {}, actual {}'.format(
                    descriptor['size'], file_stat.st_size
                )
            )
        if digest.hexdigest() != descriptor['sha256']:
            raise ValueError('replay index sha256 mismatch')

    def _add_verified_index(self, archive, index_path, descriptor):
        # Copy into an anonymous snapshot while hashing, then archive that
        # snapshot. The bytes added to the tar therefore cannot change after
        # verification, even if another process modifies the source in place.
        path_stat = os.lstat(index_path)
        if not stat.S_ISREG(path_stat.st_mode):
            raise ValueError('replay index is not a regular file')

        digest = hashlib.sha256()
        with open(index_path, 'rb') as index_file, tempfile.TemporaryFile() as snapshot:
            file_stat = os.fstat(index_file.fileno())
            if (
                    not stat.S_ISREG(file_stat.st_mode)
                    or path_stat.st_dev != file_stat.st_dev
                    or path_stat.st_ino != file_stat.st_ino
            ):
                raise ValueError('replay index file changed while opening')
            for chunk in iter(lambda: index_file.read(1024 * 1024), b''):
                digest.update(chunk)
                snapshot.write(chunk)
            snapshot_size = snapshot.tell()
            if snapshot_size != descriptor['size']:
                raise ValueError(
                    'replay index size mismatch: declared {}, actual {}'.format(
                        descriptor['size'], snapshot_size
                    )
                )
            if digest.hexdigest() != descriptor['sha256']:
                raise ValueError('replay index sha256 mismatch')

            snapshot.seek(0)
            tar_info = tarfile.TarInfo(name=descriptor['name'])
            tar_info.size = snapshot_size
            tar_info.mode = stat.S_IMODE(file_stat.st_mode)
            tar_info.mtime = int(file_stat.st_mtime)
            archive.addfile(tar_info, snapshot)

    @staticmethod
    def _add_regular_file(archive, path, archive_name, expected_size=None):
        path_stat = os.lstat(path)
        if not stat.S_ISREG(path_stat.st_mode):
            raise ValueError('replay part is not a regular file: {!r}'.format(archive_name))
        with open(path, 'rb') as source:
            file_stat = os.fstat(source.fileno())
            if (
                    not stat.S_ISREG(file_stat.st_mode)
                    or path_stat.st_dev != file_stat.st_dev
                    or path_stat.st_ino != file_stat.st_ino
            ):
                raise ValueError(
                    'replay part changed while opening: {!r}'.format(archive_name)
                )
            if expected_size is not None and file_stat.st_size != expected_size:
                raise ValueError(
                    'replay part size mismatch for {!r}: declared {}, actual {}'.format(
                        archive_name, expected_size, file_stat.st_size
                    )
                )
            tar_info = tarfile.TarInfo(name=archive_name)
            tar_info.size = file_stat.st_size
            tar_info.mode = stat.S_IMODE(file_stat.st_mode)
            tar_info.mtime = int(file_stat.st_mtime)
            archive.addfile(tar_info, source)

    def _get_verified_index_path(self, descriptor):
        index_name = descriptor['name']
        index_local_path, _ = self.find_local_part_file_path(index_name)
        local_error = None
        if index_local_path:
            index_path = os.path.join(default_storage.base_location, index_local_path)
            try:
                self._verify_index_file(index_path, descriptor)
                return index_path
            except (OSError, ValueError) as error:
                # A stale or interrupted external-storage download must not
                # poison the canonical local cache forever. Try one verified
                # refresh, while preserving the local error if no remote
                # backend is available.
                local_error = error

        validator = lambda path: self._verify_index_file(path, descriptor)
        index_local_path, url_or_error = self.download_part_file(
            index_name, validator=validator
        )
        if index_local_path:
            return os.path.join(default_storage.base_location, index_local_path)
        if local_error:
            raise local_error
        raise FileNotFoundError('{} not found: {}'.format(index_name, url_or_error))

    @staticmethod
    def _indexed_tar_matches_manifest(
            path, replay_meta_filename, manifest_sha256,
            index_descriptor, part_files,
    ):
        if not os.path.exists(path):
            return False
        try:
            with tarfile.open(path, 'r') as archive:
                expected_names = [
                    replay_meta_filename,
                    *(part_file['name'] for part_file in part_files),
                    index_descriptor['name'],
                ]
                members = archive.getmembers()
                if (
                        [member.name for member in members] != expected_names
                        or any(not member.isfile() for member in members)
                ):
                    return False

                for member, part_file in zip(members[1:-1], part_files):
                    if member.size != part_file['size']:
                        return False

                archived_meta = archive.extractfile(members[0])
                if archived_meta is None:
                    return False
                digest = hashlib.sha256()
                for chunk in iter(lambda: archived_meta.read(1024 * 1024), b''):
                    digest.update(chunk)
                if digest.hexdigest() != manifest_sha256:
                    return False

                archived_index = archive.extractfile(members[-1])
                if archived_index is None:
                    return False
                digest = hashlib.sha256()
                size = 0
                for chunk in iter(lambda: archived_index.read(1024 * 1024), b''):
                    size += len(chunk)
                    digest.update(chunk)
                return (
                    size == index_descriptor['size']
                    and digest.hexdigest() == index_descriptor['sha256']
                )
        except (KeyError, OSError, tarfile.TarError):
            return False

    def prepare_offline_tar_file(self):
        replay_meta_filename = '{}.replay.json'.format(self.obj.id)
        meta_local_path, url_or_error = self.get_part_file_path_url(replay_meta_filename)
        if not meta_local_path:
            raise FileNotFoundError(f'{replay_meta_filename} not found: {url_or_error}')
        meta_local_abs_path = os.path.join(default_storage.base_location, meta_local_path)
        meta_path_stat = os.lstat(meta_local_abs_path)
        if not stat.S_ISREG(meta_path_stat.st_mode):
            raise ValueError('replay manifest is not a regular file')
        with open(meta_local_abs_path, 'rb') as f:
            meta_stat = os.fstat(f.fileno())
            if (
                    not stat.S_ISREG(meta_stat.st_mode)
                    or meta_path_stat.st_dev != meta_stat.st_dev
                    or meta_path_stat.st_ino != meta_stat.st_ino
            ):
                raise ValueError('replay manifest changed while opening')
            meta_bytes = f.read()
        meta_data = json.loads(meta_bytes)
        if not isinstance(meta_data, dict) or not meta_data:
            raise FileNotFoundError(f'{replay_meta_filename} is empty')
        index_descriptor = self._parse_index_descriptor(meta_data)
        part_files = self._parse_part_files(
            meta_data, indexed=index_descriptor is not None
        )
        part_filenames = [part_file['name'] for part_file in part_files]
        part_sizes = {part_file['name']: part_file['size'] for part_file in part_files}
        part_paths = {}
        for part_filename in part_filenames:
            local_path, url_or_error = self.get_part_file_path_url(part_filename)
            if not local_path:
                raise FileNotFoundError(f'{part_filename} not found: {url_or_error}')
            local_abs_path = os.path.join(default_storage.base_location, local_path)
            local_file_stat = os.lstat(local_abs_path)
            if not stat.S_ISREG(local_file_stat.st_mode):
                raise ValueError(
                    'replay part is not a regular file: {!r}'.format(part_filename)
                )
            if (
                    index_descriptor
                    and local_file_stat.st_size != part_sizes[part_filename]
            ):
                raise ValueError(
                    'replay part size mismatch for {!r}: declared {}, actual {}'.format(
                        part_filename, part_sizes[part_filename],
                        local_file_stat.st_size,
                    )
                )
            part_paths[part_filename] = local_abs_path
        dir_path = os.path.dirname(meta_local_abs_path)

        index_local_abs_path = None
        if index_descriptor:
            index_local_abs_path = self._get_verified_index_path(index_descriptor)

        if index_descriptor:
            # A content-addressed filename avoids both the legacy <sid>.tar
            # and races between concurrent downloads of different manifest
            # revisions. Expired tar files are handled by replay retention.
            manifest_sha256 = hashlib.sha256(meta_bytes).hexdigest()
            offline_filename = '{}.index-v1-{}.tar'.format(
                self.obj.id, manifest_sha256
            )
        else:
            offline_filename = '{}.tar'.format(self.obj.id)
        offline_filename_abs_path = os.path.join(dir_path, offline_filename)
        cache_is_valid = os.path.exists(offline_filename_abs_path)
        if index_descriptor:
            cache_is_valid = self._indexed_tar_matches_manifest(
                offline_filename_abs_path, replay_meta_filename,
                manifest_sha256, index_descriptor, part_files,
            )
        if not cache_is_valid:
            temporary_fd, temporary_path = tempfile.mkstemp(
                prefix='{}.temporary-'.format(offline_filename), dir=dir_path
            )
            os.close(temporary_fd)
            try:
                with tarfile.open(temporary_path, 'w') as f:
                    meta_info = tarfile.TarInfo(name=replay_meta_filename)
                    meta_info.size = len(meta_bytes)
                    meta_info.mode = stat.S_IMODE(meta_stat.st_mode)
                    meta_info.mtime = int(meta_stat.st_mtime)
                    f.addfile(meta_info, io.BytesIO(meta_bytes))
                    for part_filename in part_filenames:
                        self._add_regular_file(
                            f, part_paths[part_filename], part_filename,
                            part_sizes[part_filename] if index_descriptor else None,
                        )
                    if index_descriptor:
                        self._add_verified_index(f, index_local_abs_path, index_descriptor)
                os.chmod(temporary_path, 0o644)
                os.replace(temporary_path, offline_filename_abs_path)
            finally:
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)
        return offline_filename_abs_path
