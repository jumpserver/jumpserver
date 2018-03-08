import os, re, time, shutil, magic
try:
    from PIL import Image
except ImportError:
    import Image
from hashlib import md5
from django.conf import settings
from elfinder.exceptions import ElfinderErrorMessages, NotAnImageError, DirNotFoundError
from base import ElfinderVolumeDriver

class ElfinderVolumeLocalFileSystem(ElfinderVolumeDriver):
    """
    elFinder driver for local filesystem. It implements the
    :class:`elfinder.volumes.base.ElfinderVolumeDriver` API.
    """
    
    _driver_id = 'l'
    
    def __init__(self):
        """
        Override the original __init__ method to define some 
        ElfinderVolumeLocalFileSystem-specific options.
        """
        super(ElfinderVolumeLocalFileSystem, self).__init__()
        
        #Required to count total archive files size
        self._archiveSize = 0
        
        self._options['dirMode']  = 0755 #new dirs mode
        self._options['fileMode'] = 0644 #new files mode
        
    #*********************************************************************#
    #*                        INIT AND CONFIGURE                         *#
    #*********************************************************************#
    
    def mount(self, opts):
        """
        Override the original mount method so that
        ``path`` and ``URL`` settings point to the ``MEDIA_ROOT``
        and ``MEDIA_URL`` Django settings by default.
        """

        try:
            rootpath = opts['path']
        except KeyError:
            self._options['path'] = settings.MEDIA_ROOT
            rootpath = settings.MEDIA_ROOT
        
        #attempt to create root if it does not exist
        if not os.path.exists(rootpath):
            try:
                os.makedirs(rootpath)
            except:
                raise DirNotFoundError
            
        if not 'URL' in opts or not opts['URL']:
            self._options['URL'] = settings.MEDIA_URL

        return super(ElfinderVolumeLocalFileSystem, self).mount(opts)
    
    def _configure(self):
        """
        Configure after successful mount.
        """
        self._aroot = os.path.realpath(self._root)

        super(ElfinderVolumeLocalFileSystem, self)._configure()

        #if no thumbnails url - try to detect it
        if not self._options['tmbURL'] and self._options['URL']:
            if self._options['tmbPath'].startswith(self._root):
                self._options['tmbURL'] = self._urlize(self._options['URL'] + self._options['tmbPath'][len(self._root)+1:].replace(self._separator, '/'))
            
    #*********************************************************************#
    #*                  API TO BE IMPLEMENTED IN SUB-CLASSES             *#
    #*********************************************************************#

    def _dirname(self, path):
        """
        Return parent directory path. See :func:`elfinder.volumes.base.ElfinderVolumeDriver._dirname`.
        """
        return os.path.dirname(path)

    def _basename(self, path):
        """
        Return file name. See :func:`elfinder.volumes.base.ElfinderVolumeDriver._basename`.
        """
        return os.path.basename(path)

    def _join_path(self, path1, path2):
        """
        Join two paths and return full path. If the latter path is
        absolute, return it.
        
        See :func:`elfinder.volumes.base.ElfinderVolumeDriver._join_path`.
        """
        
        return os.path.join(path1, path2)
    
    def _normpath(self, path):
        """
        Return normalized path. See :func:`elfinder.volumes.base.ElfinderVolumeDriver._normpath`.
        """
        return os.path.normpath(path)
    
    def _get_available_name(self, dir_, name, ext, i):
        """
        Get an available name for this file name.
        """

        while i <= 10000:
            n = '%s%s%s' % (name, (i if i > 0 else ''), ext)
            if not os.path.exists(self._join_path(dir_, n)):
                return n
            i+=1

        return name+md5(dir_)+ext

    #************************* file/dir info *********************#

    def _stat(self, path):
        """
        Return stat for given path. See :func:`elfinder.volumes.base.ElfinderVolumeDriver._stat`.
        """
        stat = {}

        if path != self._root and os.path.islink(path):
            target = self._readlink(path)
            if not target or target == path:
                stat['mime']  = 'symlink-broken'
                stat['read']  = False
                stat['write'] = False
                stat['size']  = 0
                return stat
            stat['alias']  = self._path(target)
            stat['target'] = target
            path  = target
            size  = os.lstat(path).st_size
        else: #raise os.error on fail
            size = os.path.getsize(path)
        
        dir_ = os.path.isdir(path)
        
        stat['mime']  = 'directory' if dir_ else self.mimetype(path)
        stat['ts'] = os.path.getmtime(path)
        stat['read']  = os.access(path, os.R_OK)
        stat['write'] = os.access(path, os.W_OK)
        if stat['read']:
            stat['size'] = 0 if dir_ else size
        return stat
   
    def _subdirs(self, path):
        """
        Return True if path is dir and has at least one childs directory
        """
        for entry in os.listdir(path):
            p = self._join_path(path, entry)
            if os.path.isdir(p) and not self._attr(p, 'hidden'):
                return True
    
    def _dimensions(self, path):
        """
        Return object width and height
        Ususaly used for images, but can be realize for video etc...
        Can Raise a NotAnImageError
        """
        try:
            im = Image.open(path)
            return '%sx%s' % im.size
        except:
            raise NotAnImageError
    
    #******************** file/dir content *********************#

    def _mimetype(self, path):
        """
        Attempt to read the file's mimetype
        """
        return magic.Magic(mime=True).from_file(path.encode('utf-8')) #unicode filename support
    
    def _readlink(self, path):
        """
        Return symlink target file
        """
        target = os.readlink(path)
        try:
            if target[0] != self._separator:
                target = self._join_path(self._dirname(path), target)
        except TypeError:
            return None
        
        atarget = os.path.realpath(target)
        if self._inpath(atarget, self._aroot):
            return self._normpath(self._join_path(self._root, atarget[len(self._aroot)+1:]))      

    def _scandir(self, path):
        """
        Return files list in directory.
        The '.' and '..' special directories are omitted.
        """
        return map(lambda x: self._join_path(path, x), os.listdir(path))

    def _fopen(self, path, mode='rb'):
        """
        Open file and return file pointer
        """
        return open(path, mode)
    
    def _fclose(self, fp, **kwargs):
        """
        Close opened file
        """
        return fp.close()
    
    def _openimage(self, path):
        """
        Open an image file.
        """
        return Image.open(path)
    
    def _saveimage(self, im, path, form):
        """
        Save an image file
        """
        im.save(path, form)
    
    #********************  file/dir manipulations *************************#
    
    def _mkdir(self, path, mode=None):
        """
        Create dir and return created dir path or raise an os.error
        """
        os.mkdir(path, mode) if mode else os.mkdir(path, self._options['dirMode']) 
        return path

    def _mkfile(self, path, name):
        """
        Create file and return it's path or False on failed
        """
        path = self._join_path(path, name)

        open(path, 'w').close()
        os.chmod(path, self._options['fileMode'])
        return path

    def _symlink(self, source, target_dir, name):
        """
        Create symlink
        """
        return os.symlink(source, self._join_path(target_dir, name))

    def _copy(self, source, target_dir, name):
        """
        Copy file into another file
        """
        return shutil.copy(source, self._join_path(target_dir, name))

    def _move(self, source, target_dir, name):
        """
        Move file into another parent dir.
        Return new file path or raise os.error.
        """
        target = self._join_path(target_dir, name)
        os.rename(source, target)
        return target
        
    def _unlink(self, path):
        """
        Remove file
        """
        return os.unlink(path)

    def _rmdir(self, path):
        """
        Remove dir
        """
        return os.rmdir(path)

    def _save(self, fp, dir_, name):
        """
        Create new file and write into it from file pointer.
        Return new file path or raise an Exception.
        """
        path = self._join_path(dir_, name)
        target = open(path, 'wb')
        
        read = fp.read(8192)
        while read:
            target.write(read)
            read = fp.read(8192)

        target.close()
        os.chmod(path, self._options['fileMode'])
        
        return path
    
    def _save_uploaded(self, uploaded_file, dir_, name, **kwargs):
        """
        Save the django UploadedFile object and return its new path
        """
        path = self._join_path(dir_, name)
        first_chunk = kwargs.get('first_chunk',False)
        chunk = kwargs.get('chunk',False)
        if chunk is False:
            target = self._fopen(path, 'wb+')
        else:
            if first_chunk is True:
                target = self._fopen(path, 'wb+')
            else:
                target = self._fopen(path, 'ab+')
        for chunk in uploaded_file.chunks():
            target.write(chunk)
        target.close()
        os.chmod(path, self._options['fileMode'])
        
        return path
    
    def _get_contents(self, path):
        """
        Get file contents
        """
        return open(path).read()

    def _put_contents(self, path, content):
        """
        Write a string to a file.
        """
        f = open(path, 'w')
        f.write(content)
        f.close()

    def _archive(self, dir_, files, name, arc):
        """
        Create archive and return its path
        """
        try:
            archiver = arc['archiver']
        except KeyError:
            raise Exception('Invalid archiver')
        
        cwd = os.getcwd()
        os.chdir(dir_)
        
        try:
            archive = archiver.open(name, "w")
            for file_ in files:
                archive.add(self._basename(file_))
            archive.close()
        except:
            raise Exception('Could not create archive')

        os.chdir(cwd)
        path = u'%s%s%s' % (dir_, self._separator, name)
        
        if not os.path.isfile(path):
            raise Exception('Could not create archive')

        return path

    def _find_symlinks(self, path):
        """
        Recursive symlinks search
        """
        if os.path.islink(path):
            return True
        
        if os.path.isdir(path):
            for p in self._scandir(path):
                if os.path.islink(p):
                    return True
                elif os.path.isdir(p) and self._find_symlinks(p):
                    return True
                elif os.path.isfile(p):
                    self._archiveSize += os.path.getsize(p)
        else:    
            self._archiveSize += os.path.getsize(path)

        return False

    def _remove_unaccepted_files(self, path):
        """
        Recursively delete unaccepted files based on their mimetype or
        accepted name and return files in the directory.
        """
        ls = []
        for p in self._scandir(path):
            mime = self.stat(p)['mime']
            if not self.mime_accepted(mime) or not self._name_accepted(self._basename(p)):
                self.remove(p)
            elif mime != 'directory' or self._remove_unaccepted_files(p):
                ls.append(p)
            self._clear_cached_stat(p)
        return ls

    def _extract(self, path, archiver):
        """
        Extract files from archive.
        """
                
        archive_name = self._basename(path)
        archive_dir = self._dirname(path)
        quarantine_dir = self._join_path(self._quarantine, u'%s%s' % (str(time.time()).replace(' ', '_'), archive_name))
        archive_copy = self._join_path(quarantine_dir, archive_name)
        
        self._mkdir(quarantine_dir)

        #copy archive file in quarantine
        self._copy(path, quarantine_dir, archive_name)
        
        #extract in quarantine
        self._unpack(archive_copy, archiver)
        self._unlink(archive_copy)
        
        ls = self._remove_unaccepted_files(quarantine_dir)
        self._archiveSize = 0
        
        #find symlinks            
        if self._find_symlinks(quarantine_dir):
            raise Exception(ElfinderErrorMessages.ERROR_ARC_SYMLINKS)

        #check max files size
        if self._options['archiveMaxSize'] > 0 and self._options['archiveMaxSize'] < self._archiveSize:
            raise Exception(ElfinderErrorMessages.ERROR_ARC_MAXSIZE)

        #for several files - create new directory
        #create unique name for directory
        if len(ls) >= 1:    
            name = archive_name
            m =re.search(r'\.((tar\.(gz|bz|bz2|z|lzo))|cpio\.gz|ps\.gz|xcf\.(gz|bz2)|[a-z0-9]{1,4})$', name, re.IGNORECASE) 
            if m and m.group(0):
                name = name[0:len(name)-len(m.group(0))]

            test = self._join_path(archive_dir, name)
            if os.path.exists(test) or os.path.islink(test):
                name = self._unique_name(archive_dir, name, ' extracted', False)

            self._move(quarantine_dir, archive_dir, name)
            result  = self._join_path(archive_dir, name)
        else:
            os.rmdir(quarantine_dir)
            raise Exception('No valid files in archive')
        
        if not os.path.exists(result):
            raise Exception('Could not extract archive')
        
        return result