from django.utils.translation import ugettext as _

class ElfinderErrorMessages:
    """
    Standard error message codes, the text message of which is handled by the 
    elFinder client
    """

    ERROR_UNKNOWN = 'errUnknown'
    ERROR_UNKNOWN_CMD = 'errUnknownCmd'
    ERROR_CONF = 'errConf'
    ERROR_CONF_NO_JSON = 'errJSON'
    ERROR_CONF_NO_VOL = 'errNoVolumes'
    ERROR_INV_PARAMS = 'errCmdParams'
    ERROR_OPEN = 'errOpen'
    ERROR_DIR_NOT_FOUND = 'errFolderNotFound'
    ERROR_FILE_NOT_FOUND = 'errFileNotFound' #'File not found.'
    ERROR_TRGDIR_NOT_FOUND = 'errTrgFolderNotFound' #'Target folder "$1" not found.'
    ERROR_NOT_DIR = 'errNotFolder'
    ERROR_NOT_FILE = 'errNotFile'
    ERROR_PERM_DENIED = 'errPerm'
    ERROR_LOCKED = 'errLocked' #'"$1" is locked and can not be renamed, moved or removed.'
    ERROR_EXISTS = 'errExists' #'File named "$1" already exists.'
    ERROR_INVALID_NAME = 'errInvName' #'Invalid file name.'
    ERROR_MKDIR = 'errMkdir'
    ERROR_MKFILE = 'errMkfile'
    ERROR_RENAME = 'errRename'
    ERROR_COPY = 'errCopy'
    ERROR_MOVE  = 'errMove'
    ERROR_COPY_FROM = 'errCopyFrom'
    ERROR_COPY_TO = 'errCopyTo'
    ERROR_COPY_ITSELF = 'errCopyInItself'
    ERROR_REPLACE = 'errReplace' #'Unable to replace "$1".'
    ERROR_RM = 'errRm' #'Unable to remove "$1".'
    ERROR_RM_SRC = 'errRmSrc' #'Unable remove source file(s)'
    ERROR_UPLOAD = 'errUpload' #'Upload error.'
    ERROR_UPLOAD_FILE = 'errUploadFile' #'Unable to upload "$1".'
    ERROR_UPLOAD_NO_FILES = 'errUploadNoFiles' #'No files found for upload.'
    ERROR_UPLOAD_TOTAL_SIZE = 'errUploadTotalSize' #'Data exceeds the maximum allowed size.'
    ERROR_UPLOAD_FILE_SIZE = 'errUploadFileSize' #'File exceeds maximum allowed size.'
    ERROR_UPLOAD_FILE_MIME = 'errUploadMime' #'File type not allowed.'
    ERROR_UPLOAD_TRANSFER = 'errUploadTransfer' #'"$1" transfer error.'
    ERROR_ACCESS_DENIED = 'errAccess'
    ERROR_NOT_REPLACE = 'errNotReplace' #Object "$1" already exists at this location and can not be replaced with object of another type.
    ERROR_SAVE = 'errSave'
    ERROR_EXTRACT = 'errExtract'
    ERROR_ARCHIVE = 'errArchive'
    ERROR_NOT_ARCHIVE = 'errNoArchive'
    ERROR_ARCHIVE_TYPE = 'errArcType'
    ERROR_ARC_SYMLINKS = 'errArcSymlinks'
    ERROR_ARC_MAXSIZE = 'errArcMaxSize'
    ERROR_RESIZE = 'errResize'
    ERROR_UNSUPPORT_TYPE = 'errUsupportType'
    ERROR_NOT_UTF8_CONTENT  = 'errNotUTF8Content'
    ERROR_NETMOUNT = 'errNetMount'
    ERROR_NETMOUNT_NO_DRIVER = 'errNetMountNoDriver'
    ERROR_NETMOUNT_FAILED = 'errNetMountFailed'

class VolumeNotFoundError(Exception):
    def __init__(self):
        super(VolumeNotFoundError, self).__init__(_("Volume could not be found"))
    
class FileNotFoundError(Exception):
    def __init__(self):
        super(FileNotFoundError, self).__init__(ElfinderErrorMessages.ERROR_FILE_NOT_FOUND)
        
class DirNotFoundError(Exception):
    def __init__(self):
        super(DirNotFoundError, self).__init__(ElfinderErrorMessages.ERROR_DIR_NOT_FOUND)
        
class PermissionDeniedError(Exception):
    def __init__(self):
        super(PermissionDeniedError, self).__init__(ElfinderErrorMessages.ERROR_PERM_DENIED)

class NamedError(Exception):
    """
    Elfinder-specific exception. 
    `msg` contains the error code
    `name` holds the path for which operation failed
    """
    def __init__(self, msg, name):
        self.name = name
        super(NamedError, self).__init__(msg)
        
class NotAnImageError(Exception):
    def __init__(self):
        super(NotAnImageError, self).__init__(_('This is not a valid image file'))