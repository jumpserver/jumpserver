from zipfile import ZipFile


class ZipFileArchiver(object):
    """
    An archiver used to generate .zip files.
    This wraps Python's built in :class:`zipfile.ZipFile`
    methods to operate exactly like :class:`tarfile.TarFile` does.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Create a :class:`.ZipFileArchiver` instance. We create a new
        :class:`zipfile.ZipFile` and store it to the ``zipfile`` member. 
        """
        self.zipfile = ZipFile(*args, **kwargs)
    
    @classmethod
    def open(self, *args, **kwargs):
        """
        Open the archive. This must be a classmethod.
        """
        return ZipFileArchiver(*args,**kwargs) 
    
    def add(self, *args, **kwargs):
        """
        Add file to the archive.
        """
        self.zipfile.write(*args, **kwargs)
    
    def extractall(self, *args, **kwargs):
        """
        Extract all files from the archive.
        """
        self.zipfile.extractall(*args, **kwargs)

    def close(self):
        """
        Close the archive.
        """
        self.zipfile.close()
