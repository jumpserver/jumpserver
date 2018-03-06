import os, re, magic, time, tempfile, shutil, mimetypes
try:
    from PIL import Image
except ImportError:
    import Image
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.core.files import File as DjangoFile
#from django.utils.importlib import import_module
from importlib import import_module
from elfinder.exceptions import NotAnImageError, ElfinderErrorMessages
from base import ElfinderVolumeDriver

class ElfinderVolumeStorage(ElfinderVolumeDriver):
    """
    elFinder driver for `Django file storages <https://docs.djangoproject.com/en/dev/topics/files/#file-storage>`_.
    It implements the
    :class:`elfinder.volumes.base.ElfinderVolumeDriver` API.
    
    Due to the Django filesystem storage API not supporting all operations (i.e. it is 
    intended for use with file and not directory manipulations), you should
    take at look at the :func:`elfinder.volumes.storage.ElfinderVolumeStorage._configure`
    method to understand how this driver operates on certain scenarios.
    
    For more information on how to specify the storage instance that the
    driver will use, take a look at the
    :func:`elfinder.volumes.storage.ElfinderVolumeStorage.mount` method.
    
    .. note::
     
        This driver might be require a large amount of memory on some
        operations such as copy and remove when using large files. 
    """

    _driver_id = 's'
    
    #*********************************************************************#
    #*                        INIT AND CONFIGURE                         *#
    #*********************************************************************#
    
    def mount(self, opts):
        """
        This method mounts the driver.
        
        A 'storage' option must be set and point to
        a valid file storage instance. Alternatively, you can define the
        'storageClass' and 'storageKwArgs' options to let driver
        instantiate the storage. The latter method is useful when the
        storage depends on other django settings, since yawd-elfinder 
        reads custom optionsets from the settings.py module as well.
        
        .. note:: 
            
            The 'storageClass' argument can also be a string to
            to the absolute pythonpath of the class (e.g. 
            'django_dropbox.storage.DropoxStorage')
        
        The provided storage must implement both 
        `listdir() <https://docs.djangoproject.com/en/dev/ref/files/storage/#django.core.files.storage.Storage.listdir>`_
        and `url() <https://docs.djangoproject.com/en/dev/ref/files/storage/#django.core.files.storage.Storage.url>`_
        methods to be valid.
        """
        if "key_label" in opts['storageKwArgs'].keys():
            self._key_label = opts['storageKwArgs']['key_label']
            del opts['storageKwArgs']['key_label']
        if not 'storage' in opts:
            if not 'storageClass' in opts:
                opts['storage']  = FileSystemStorage()
            else:
                
                #load the class if string
                if isinstance(opts['storageClass'], basestring):
                    split = opts['storageClass'].split('.')
                    storage_module = import_module('.'.join(split[:-1]))
                    opts['storageClass'] = getattr(storage_module, split[-1])
        
                if not 'storageKwArgs' in opts:
                    opts['storageKwArgs'] = {}
                #store in opts so that the instantiation happens only once
                opts['storage'] = opts['storageClass'](**opts['storageKwArgs'])

                #do not accept the storage if listdir or url are not implemented
                try:
                    opts['storage'].listdir(self._root)
                    opts['storage'].url(self._root)
                except NotImplementedError:
                    raise Exception('Storage %s should implement both the listdir() and url() methods to be valid for use with yawd-elfinder.' % self._options['storage'].__class__)

        #set default path and URL
        self._options['path'] = '.'
        if (not 'URL' in opts or not opts['URL']):
            self._options['URL'] = opts['storage'].url(self._root) 
            
        if not 'alias' in opts or not opts['alias']:
            self._options['alias'] = opts['storage'].__class__.__name__
        
        return super(ElfinderVolumeStorage, self).mount(opts)
        
    def _configure(self):
        """
        If the storage does not implement the 
        `delete() <https://docs.djangoproject.com/en/dev/ref/files/storage/#django.core.files.storage.Storage.delete>`_
        method, the `'rm'` command will be disabled.
        
        As the storage API does not support removing directories, this
        driver will not allow removing directories by default,
        unless an :ref:`setting-rmDir` option is provided. `'rmDir'` must be a callable
        that accepts a single dir path argument and deletes it. If the 
        storage is an instance of Django's own default FileSystemStorage, 
        the driver uses a built-in `'rmDir'` callback. Note that the 
        storage's delete() method must also be implemented, otherwise 
        `'rm'` command will be disabled anyway.
    
        As far as thumbnails are concerned, if :ref:`setting-tmbPath` is absolute
        an exception will be thrown. 
        """
        
        #if tmbPath is relative store thumbnails in the storage   
        if not self._isabs(self._options['tmbPath']):
            super(ElfinderVolumeStorage, self)._configure()
            
            if not self._options['tmbURL'] and self._options['URL']:
                self._options['tmbURL'] = self._options['URL'] + self._options['tmbPath'][len(self._root)+1:].replace(self._separator, '/') + '/'
        
        #if tmbPath is absolute try to create the directory locally
        elif self._isabs(self._options['tmbPath']):
            raise Exception('tmbPath must be relative')
        
        #disable rm command if delete is not implemented
        try:
            #check against a non-existing file
            self._options['storage'].delete(self.encode(str(time.time())))
        except NotImplementedError:
            if not 'rm' in self._options['disabled']:
                self._options['disabled'].append('rm')
        except:
            pass
        
        #disable rmdir command if a custom implementation is not provided
        if not 'rmDir' in self._options or not callable(self._options['rmDir']):
            if isinstance(self._options['storage'], FileSystemStorage):
                self._options['rmDir'] = self._rmdir_callable
            elif not 'rmdir' in self._options['disabled']:  # cancel delete disable directory
                pass
                # self._options['disabled'].append('rmdir')

    #*********************************************************************#
    #*                  API TO BE IMPLEMENTED IN SUB-CLASSES             *#
    #*********************************************************************#
    
    def _dirname(self, path):
        """
        Return parent directory path. Return stat for given path. See :func:`elfinder.volumes.base.ElfinderVolumeDriver._dirname`.
        """
        return self._separator.join(path.split(self._separator)[:-1])

    def _basename(self, path):
        """
        Return file name.
        See :func:`elfinder.volumes.base.ElfinderVolumeDriver._basename`.
        """
        return path.split(self._separator)[-1]

    def _join_path(self, path1, path2):
        """
        Join two paths and return full path. If the latter path is
        absolute, return it. This does not use the default
        :py:func:`os.path.join`
        implementation as we might be operating on a remote system.
        
        Return stat for given path. See :func:`elfinder.volumes.base.ElfinderVolumeDriver._join_path`.
        """
        
        if self._separator == '\\' and re.match(r'([a-zA-Z]+:)?\\$', path2):
            return path2
        elif path2.startswith(self._separator):
            return path2

        if not path1.endswith(self._separator):
            return '%s%s%s' % (path1, self._separator, path2)
        else:
            return '%s%s' % (path1, path2)
        
    def _normpath(self, path):
        """
        Return normalized path. The root path of this driver is always `'.'`,
        so we just need to return the path.
        
        Return stat for given path. See :func:`elfinder.volumes.base.ElfinderVolumeDriver._normpath`.
        """
        
        if path[-1] == self._separator:
            return path[:-1]

        return path
    
    def _get_available_name(self, dir_, name, ext, i):
        """
        Get an available name for this file name.
        """
        path = self._options['storage'].get_available_name(self._join_path(dir_, '%s%s' % (name, ext)))
        return self._basename(path)

    #************************* file/dir info *********************# 
  
    def _stat(self, path):
        """
        Return stat for given path. See
        :func:`elfinder.volumes.base.ElfinderVolumeDriver._stat`.
        """
        stat = {}

        if not self._options['storage'].exists(path):
            raise os.error
        
        try:
            stat['mime'] = self.mimetype(path)
            try:
                stat['size'] = self._options['storage'].size(path)
            except NotImplementedError:
                stat['size'] = 0
        except:
            stat['mime'] = 'directory'
            stat['size'] = 0            
        try:
            stat['ts'] = time.mktime(self._options['storage'].modified_time(path).timetuple())
        except NotImplementedError:
            stat['ts'] = ''
            
        stat['read']  = True
        stat['write'] = True
        return stat
    
    def _subdirs(self, path):
        """
        Return ``True`` if path is a directory and has at least one
        child directory.
        """
        try:
            for entry in self._options['storage'].listdir(path)[0]:
                if not self._attr(self._join_path(path, entry), 'hidden'):
                    return True
        except NotImplementedError:
            pass
        
    def _dimensions(self, path):
        """
        Return object width and height.
        Ususaly used for images. It could raise a ``NotAnImageError``
        exception.
        """
        try:
            im = self._openimage(path)
            return '%sx%s' % im.size
        except:
            raise NotAnImageError

    #******************** file/dir content *********************#

    def _mimetype(self, path):
        """
        Attempt to read the file's mimetype.
        """
        file_name = str(path.split("/")[-1]).strip()

        if re.search(r'^\./proc/', path) or re.search(r'^\./sys/', path):  # handler /proc /path
            if file_name in self._files:  # handler is files
                try:
                    fp = self._fopen(path)
                    mime = magic.Magic(mime=True).from_buffer(fp.read(10))  # read 10 bytes
                    fp.close()
                    return mime
                except:
                    return "application/empty"

        # not  handler /dev directory slink
        if re.search(r'^\./dev/', path) and self._files[file_name] in 'l':
            return "application/empty"

        if file_name in self._files:
            if self._files[file_name] not in '-l':  # is not normal file link
                return "application/empty"
        fp = self._fopen(path)
        mime = magic.Magic(mime=True).from_buffer(fp.read(10))  # read 10 bytes
        fp.close()
        return mime
    
    def _scandir(self, path):
        """
        Return files list in directory.
        The '.' and '..' special directories are omitted.
        """
        try:
            all_ = self._options['storage'].listdir(path)
            self._files = all_[2]
            return map(lambda x: self._join_path(path, x), all_[0]+all_[1])
        except NotImplementedError:
            return []
        
    def _fopen(self, path, mode='rb'):
        """
        Open file and return a file pointer.
        """
        return self._options['storage'].open(path, mode)
    
    def _fclose(self, fp, **kwargs):
        """
        Close opened file.
        """
        return fp.close()
    
    def _openimage(self, path):
        """
        Open an image file.
        """
        fp = self._fopen(path)
        #place the file contents in a temp file
        #this is necessary for remote storages, since PIL reads contents byte-by-byte
        tmp_file = tempfile.TemporaryFile()
        tmp_file.write(fp.read())
        fp.close()
        
        tmp_file.seek(0)
        im = Image.open(tmp_file)
        
        return im
        
    def _saveimage(self, im, path, form):
        """
        Save an image file.
        """
        #PIL saves only in binary mode
        tmp_file = tempfile.TemporaryFile()
        im.save(tmp_file, form)
        tmp_file.seek(0)
        
        fp = self._fopen(path, 'w+')
        fp.write(tmp_file.read())
        tmp_file.close()
        fp.close()

    #********************  file/dir manipulations *************************#
    
    def _mkdir(self, path, mode=None):
        """
        Create dir and return created dir path or raise an os.error. Due to
        the storage API not dealing with directory creation, this implementation
        will attempt to create an empty temporary file inside the specified path.
        This way the parent folder will also be created. The temp file will be
        be deleted on exit.
        """
        
        fname = '.%s-mkdir' % self.encode(path)

        #on failure this will raise an os.error
        self._mkfile(path, fname)
        self._unlink(self._join_path(path, fname))

        return path
    
    def _mkfile(self, path, name):
        """
        Create file and return it's path or rais an ``os.error`` on fail.
        """
        try:
            return self._options['storage'].save(self._join_path(path, name), ContentFile(''))
        except:
            raise os.error
    
    def _copy(self, source, target_dir, name):
        """
        Copy file into another file.
        """
        fp = self._fopen(source)
        
        #place the file contents in a temp file
        #this is necessary for remote storages since reading in chunks may not be supported
        tmp_file = tempfile.NamedTemporaryFile()
        tmp_file.write(fp.read())
        fp.close()

        self._options['storage'].save(self._join_path(target_dir, name), DjangoFile(tmp_file))
        tmp_file.close()
        
    def _move(self, source, target_dir, name):
        """
        Move file into a different parent directory.
        Return new file path or raise ``os.error``.
        """
        
        stat = self.stat(source)
        try:
            if stat['mime'] == 'directory':
                dest = self._join_path(target_dir, name)
                self._mkdir(dest)
                for p in self._get_cached_dir(source):
                    self._move(p, dest, self._basename(p))
                self._rmdir(source)
            else:
                self._copy(source, target_dir, name)
                self._unlink(source)
        except:
            raise os.error
            
        return self._join_path(target_dir, name)

    def _unlink(self, path):
        """
        Remove the ``path`` file.
        """
        try:
            self._options['storage'].delete(path)
            return True
        except:
            return False
        
    def _rmdir(self, path):
        """
        Remove a directory. This implementation calls the 
        :ref:`setting-rmDir` callable driver option, if it is available.
        If not, it raises an ``os.error``.
        """
        if 'rmDir' in self._options:
            return self._options['storage'].delete_dir(path)
        raise os.error
            
    def _rmdir_callable(self, path, storage):
        """
        Remove directory when using a 
        `FileSystemStorage <https://docs.djangoproject.com/en/dev/ref/files/storage/#the-filesystemstorage-class>`_
        storage backend. See also the :ref:`setting-rmDir` setting.
        """
        return os.rmdir(self._join_path(storage.location, path))
    
    def _save(self, fp, dir_, name):
        """
        Create new file and write into it from file pointer.
        Return new file path or raise an ``Exception``.
        """
        
        #place the file contents in a temp file
        #this is necessary for remote storages since reading in chunks may not be supported
        tmp_file = tempfile.NamedTemporaryFile()
        tmp_file.write(fp.read())
        fp.close()
        tmp_file.seek(0)
        
        path = self._join_path(dir_, name)
        self._options['storage'].save(path, DjangoFile(tmp_file))
        tmp_file.close()
        
        return path
        
    def _save_uploaded(self, uploaded_file, dir_, name, chunk_name, is_first_chunk, **kwargs):
        """
        Save the Django
        `UploadedFile <https://docs.djangoproject.com/en/dev/topics/http/file-uploads/#django.core.files.uploadedfile.UploadedFile>`_
        object and return its new path.
        """
        path = self._join_path(dir_, name)
        if chunk_name and is_first_chunk:
            target = self._fopen(path, 'w+')
        elif chunk_name:
            target = self._fopen(path, 'a+')
        else:
            target = self._fopen(path, 'w+')
        for chunk in uploaded_file.chunks():
            target.write(chunk)
        target.close()
        return path
    
    def _get_contents(self, path):
        """
        Get file contents
        """
        return self._fopen(path, 'rb').read()

    def _put_contents(self, path, content):
        """
        Write a string to a file.
        """
        f = self._fopen(path, 'w+')
        f.write(content)
        f.close()
        
    def _archive_copy(self, file_, dest):
        stat = self.stat(file_)
        dest_path = os.path.join(dest, self._basename(file_))
        if stat['mime'] == 'directory':
            #use os.path.join because we operate on the local filesystem
            os.mkdir(dest_path)
            for p in self._get_cached_dir(file_):
                self._archive_copy(p, dest_path)
        else:
            fp = self._fopen(file_)
            #place the file contents in a temp file
            #this is necessary for remote storages since reading in chunks may not be supported
            tmp_file = open(dest_path, 'w+')
            tmp_file.write(fp.read())
            fp.close()
            tmp_file.close()

    def _archive(self, dir_, files, name, arc):
        """
        Create a new archive file and return its path. This implementation
        temporarily copies the remote storage files to the **local
        filesystem** to accomplish quick access. Perhaps you would
        like to check the
        :ref:`setting-quarantine` setting to control where temporary files
        will be stored.
        """
        try:
            archiver = arc['archiver']
        except KeyError:
            raise Exception('Invalid archiver')
        
        quarantine_dir = os.path.join(self._options['quarantine'], '%s-temp' % name)
        
        if os.path.exists(quarantine_dir):
            if not os.path.isdir(quarantine_dir):
                raise Exception('Could not create temporary directory')
            else:
                shutil.rmtree(quarantine_dir)
        #print os.getcwd()
        os.mkdir(quarantine_dir)
        
        for file_ in files:
            self._archive_copy(file_, quarantine_dir)
        
        files = os.listdir(quarantine_dir)
        cwd = os.getcwd()
        os.chdir(quarantine_dir)
        
        archive = archiver.open(name, "w")
        for file_ in files:
            archive.add(file_)
        archive.close()

        path = self._join_path(dir_, name)
        fp = self._fopen(path, 'w+')
        fp.write(open(name).read())
        fp.close()
        
        os.chdir(cwd)
        shutil.rmtree(quarantine_dir)

        return path
    
    def _local_file_mimetype(self, path, name = ''):
        """
        Return local file mimetype. Used on quarantined files.  
        """
        if os.path.isdir(path):
            return 'directory'

        mime = magic.Magic(mime=True).from_file(path.encode('utf-8')) #unicode filename support
        int_mime = None

        if not mime or mime in ['inode/x-empty', 'application/empty']:
            int_mime = mimetypes.guess_type(name if name else path)[0]

        return int_mime if int_mime else mime
    
    def _local_dir_size(self, path):
        """
        Get the size of items in the ``path`` directory.
        """
        size = 0
        ls = map(lambda x:os.path.join(path, x), os.listdir(path))
        for p in ls:
            if os.path.isdir(p):
                size += self._local_dir_size(p)
            else:
                size += os.path.getsize(p)
        return size

    def _remove_unaccepted_files(self, path):
        """
        Recursively delete unaccepted files based on their mimetype
        and return the final number or files in the directory.
        """
        ls = []
        for p in map(lambda x:os.path.join(path, x), os.listdir(path)):
            if os.path.islink(p):
                raise Exception(ElfinderErrorMessages.ERROR_ARC_SYMLINKS)
            mime = self._local_file_mimetype(p)
            if not self.mime_accepted(mime) or not self._name_accepted(self._basename(p)):
                if mime != 'directory':
                    os.unlink(p)
                else:
                    shutil.rmtree(p)
            elif mime != 'directory' or self._remove_unaccepted_files(p):
                ls.append(p)
        return ls
    
    def _move_from_local(self, path, dst, name):
        """
        Move from local file to storage file.
        """
        if os.path.isdir(path):
            for p in map(lambda x:os.path.join(path, x), os.listdir(path)):
                self._move_from_local(p, self._join_path(dst, name), os.path.basename(p))
            shutil.rmtree(path)
        else:
            dst_path = self._join_path(dst, name)
            fp = open(path)
            self._options['storage'].save(dst_path, DjangoFile(fp))
            fp.close()
            os.unlink(path)
    
    def _extract(self, path, archiver):
        """
        Extract files from archive.
        """
        #print os.getcwd() 
        archive_name = self._basename(path)
        archive_dir = self._dirname(path)
        quarantine_dir = self._join_path(self._quarantine, u'%s%s' % (str(time.time()).replace(' ', '_'), archive_name))
        archive_copy = self._join_path(quarantine_dir, archive_name)
        
        os.mkdir(quarantine_dir)

        #copy archive file in quarantine
        self._archive_copy(path, quarantine_dir)
        
        #extract in quarantine
        self._unpack(archive_copy, archiver)
        os.unlink(archive_copy)
        
        try:
            ls = self._remove_unaccepted_files(quarantine_dir)
        except:
            shutil.rmtree(quarantine_dir)
            raise

        #check max files size
        if self._options['archiveMaxSize'] > 0 and self._options['archiveMaxSize'] < self._local_dir_size(quarantine_dir):
            raise Exception(ElfinderErrorMessages.ERROR_ARC_MAXSIZE)

        #for several files - create new directory
        #create unique name for directory
        if len(ls) >= 1:
        
            name = archive_name
            m =re.search(r'\.((tar\.(gz|bz|bz2|z|lzo))|cpio\.gz|ps\.gz|xcf\.(gz|bz2)|[a-z0-9]{1,4})$', name, re.IGNORECASE) 
            if m and m.group(0):
                name = name[0:(len(name)-len(m.group(0)))]

            test = self._join_path(archive_dir, name)
            if self._options['storage'].exists(test):
                name = self._unique_name(archive_dir, name, ' extracted', False)

            self._move_from_local(quarantine_dir, archive_dir, name)
            result  = self._join_path(archive_dir, name)
        else:
            os.rmdir(quarantine_dir)
            raise Exception('No valid files in archive')
        
        return result
