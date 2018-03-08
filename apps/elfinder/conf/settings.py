from os.path import join
from django.conf import settings
from elfinder.utils.accesscontrol import fs_standard_access
from elfinder.volumes.filesystem import ElfinderVolumeLocalFileSystem
from elfinder.volumes.storage import ElfinderVolumeStorage
ELFINDER_JS_URLS = {
    'a_jquery' : 'http://apps.bdimg.com/libs/jquery/1.8.2/jquery.min.js',
    'b_jqueryui' : 'http://apps.bdimg.com/libs/jqueryui/1.9.2/jquery-ui.min.js',
    'c_elfinder' : '%selfinder/js/elfinder.full.js' % settings.STATIC_URL,
}
#allow to override any key in the project settings file   
ELFINDER_JS_URLS.update(getattr(settings, 'ELFINDER_JS_URLS', {}))

ELFINDER_CSS_URLS = {
    'a_jqueryui' : 'http://apps.bdimg.com/libs/jqueryui/1.9.2/themes/smoothness/jquery-ui.css',
    'b_elfinder' : '%selfinder/css/elfinder.min.css' % settings.STATIC_URL
}
#allow to override any key in the project settings file   
ELFINDER_CSS_URLS.update(getattr(settings, 'ELFINDER_CSS_URLS', {}))

ELFINDER_WIDGET_JS_URL = '%sjs/jquery.elfinder-widget.full.js' % settings.STATIC_URL
ELFINDER_WIDGET_CSS_URL = '%scss/jquery.elfinder-widget.full.css' % settings.STATIC_URL

ELFINDER_LANGUAGES_ROOT_URL = getattr(settings, 'ELFINDER_LANGUAGES_ROOT_URL', '%splugins/elfinder/js/i18n/' % settings.STATIC_URL)

#The available language codes. A corresponding ELFINDER_LANGUAGES_ROOT_URL/elfinder.{ext}.js url must be available  
ELFINDER_LANGUAGES = getattr(settings, 'ELFINDER_LANGUAGES', ['ar', 'bg', 'ca', 'cs', 'de', 'el', 'es', 'fa', 'fr', 'hu', 'it', 'jp', 'ko', 'nl', 'no', 'pl', 'pt_BR', 'ru', 'tr', 'zh_CN'])

ELFINDER_CONNECTOR_OPTION_SETS = {
    #the default keywords demonstrates all possible configuration options
    #it allowes all file types, except from hidden files
    'default' : {
        'debug' : True, #optionally set debug to True for additional debug messages
        'roots' : [ 
            #{
            #    'driver' : ElfinderVolumeLocalFileSystem,
            #    'path'  : join(settings.MEDIA_ROOT, 'files'),
            #},
            {
                'id' : 'lff',
                'driver' : ElfinderVolumeLocalFileSystem,
                'path' : join(settings.MEDIA_ROOT, u'files'),
                'alias' : 'Files',
                #open this path on initial request instead of root path
                #'startPath' : '',
                'URL' : '%sfiles/' % settings.MEDIA_URL,
                #the depth of sub-directory listings that should return per request
                #'treeDeep' : 1,
                #directory separator. required by client to show paths correctly
                #'separator' : os.sep,
                #directory for thumbnails
                #'tmbPath' : '.tmb',
                #Thumbnails dir URL. Set this if you're storing thumbnails outside the root directory
                #'tmbURL' : '',
                #Thumbnail size (in px)
                #'tmbSize' : 48,
                #Whether to crop (scale image to fit) thumbnails or not.
                #'tmbCrop' : True,
                #thumbnails background color (hex #rrggbb or 'transparent')
                #'tmbBgColor' : '#ffffff',
                #on paste file -  if True - old file will be replaced with new one, if False new file get name - original_name-number.ext
                'copyOverwrite' : False,
                #if True - join new and old directories content on paste
                #'copyJoin' : True,
                #filter mime types to show
                #'onlyMimes' : [],
                #on upload -  if True - old file will be replaced with new one, if False new file get name - original_name-number.ext
                #'uploadOverwrite' : True,
                #mimetypes allowed to upload
                'uploadAllow' : ['all',],
                #mimetypes not allowed to upload
                'uploadDeny' : ['all',],
                #order to proccess uploadAllow and uploadDeny options
                'uploadOrder' : ['deny', 'allow'],
                #maximum upload file size. NOTE - this is size for every uploaded files
                #The maximum upload file size. Set as number (bytes) or string ending with the size unit (e.g. "10M", "500K", "1G")
                'uploadMaxSize' : '128m',
                #if True - every folder will be check for children folders, otherwise all folders will be marked as having subfolders
                #'checkSubfolders' : True,
                #allow to copy from this volume to other ones?
                #'copyFrom' : True,
                #allow to copy from other volumes to this one?
                #'copyTo' : True,
                #Regular expression against which all new file names will be validated.
                #'disabled' : [],
                #regexp against which new file names will be validated
                #enable this to allow creating hidden files
                #'acceptedName' : r'.*',
                #callable to control file permissions
                #`fs_standard_access` hides all files starting with .
                'accessControl' : fs_standard_access,
                #default permissions. not set hidden/locked here - take no effect
                #'defaults' : {
                #    'read' : True,
                #    'write' : True
                #},
                'attributes' : [
                    {
                        'pattern' : r'\.tmb$',
                        'read' : True,
                        'write': True,
                        'hidden' : True,
                        'locked' : True
                    },
                    #{   
                    #    'pattern' : r'\/my-inaccessible-folder$',
                    #    'write' : False,
                    #    'read' : False,
                    #    'hidden' : True,
                    #    'locked' : True
                    #},
                ],
                #quarantine folder name - required to check archive (must be hidden)
                #'quarantine' : '.quarantine',
                #Allowed archive's mimetypes to create. Leave empty for all available types.
                #'archiveMimes' : [],
                #Manual config for archivers. Leave empty for auto detect
                'archivers' : {
                    #create archivers must be a dictionary containing a class implementing the open, add, close methods and the archiver's file extension
                    #they should operate like the python's built-in tarfile.TarFile classes
                    #http://docs.python.org/library/tarfile.html
                    #'create' : { 'ext' : 'rar', 'archiver' : MyRarArchiver },
                    #extract archiver class must implement the open, extractall and close methods
                    #they should operate like python's built-in tarfile.TarFile classes
                    #for more information see http://docs.python.org/library/tarfile.html
                    #'extract' : { 'ext' : 'rar', 'archiver' : MyRarExtractor },
                },
                #seconds to cache the file and dir data used by the driver 
                'cache' : 6
            },
            {
                'id' : 'lffim',
                'driver' : ElfinderVolumeLocalFileSystem,
                'path' : join(settings.MEDIA_ROOT, u'images'),
                'alias' : 'Elfinder images',
                'URL' : '%simages/' % settings.MEDIA_URL,
                'onlyMimes' : ['image',],
                'uploadAllow' : ['image',],
                'uploadDeny' : ['all',],
                'uploadMaxSize' : '128m',
                'disabled' : ['mkfile', 'archive'],
                'accessControl' : fs_standard_access,
                'attributes' : [
                    {
                        'pattern' : r'\.tmb$',
                        'read' : True,
                        'write': True,
                        'hidden' : True,
                        'locked' : True
                    },
                ],
            },
            {
                'id' : 'lffimsa',
                'driver' : ElfinderVolumeLocalFileSystem,
                'path' : join(settings.MEDIA_ROOT, u'pdf'),
                'alias' : 'pdf',
                'URL' : '%spdf/' % settings.MEDIA_URL,
                'onlyMimes' : ['application/pdf',],
                'uploadAllow' : ['application/pdf',],
                'uploadDeny' : ['all',],
                'uploadMaxSize' : '128m',
                'disabled' : ['mkfile', 'archive'],
                'accessControl' : fs_standard_access,
                'attributes' : [
                    {
                        'pattern' : r'\.tmb$',
                        'read' : True,
                        'write': True,
                        'hidden' : True,
                        'locked' : True
                    },
                ],
            } 
        ]
    },
    #option set to only allow image files
    'image' : {
        'debug' : True,
        'roots' : [
            {
                'id' : 'imageid',
                'driver' : ElfinderVolumeLocalFileSystem,
                'path' : join(settings.MEDIA_ROOT, u'images'),
                'alias' : 'Elfinder images',
                'URL' : '%simages/' % settings.MEDIA_URL,
                'onlyMimes' : ['image',],
                'uploadAllow' : ['image',],
                'uploadDeny' : ['all',],
                'uploadMaxSize' : '128m',
                'disabled' : ['mkfile', 'archive'],
                'accessControl' : fs_standard_access,
                'attributes' : [
                    {
                        'pattern' : r'\.tmb$',
                        'read' : True,
                        'write': True,
                        'hidden' : True,
                        'locked' : True
                    },
                ],
            }
        ]  
    },
    'pdf':{
        'debug':True,
        'roots':[
            {
                'id' : 'pdf',
                'driver' : ElfinderVolumeLocalFileSystem,
                'path' : join(settings.MEDIA_ROOT, u'pdf'),
                'alias' : 'pdf',
                'URL' : '%spdf/' % settings.MEDIA_URL,
                'onlyMimes' : ['application/pdf',],
                'uploadAllow' : ['application/pdf',],
                'uploadDeny' : ['all',],
                'uploadMaxSize' : '128m',
                'disabled' : ['mkfile', 'archive'],
                'accessControl' : fs_standard_access,
                'attributes' : [
                    {
                        'pattern' : r'\.tmb$',
                        'read' : True,
                        'write': True,
                        'hidden' : True,
                        'locked' : True
                    },
                ],
            }             
        ]
        },
    'sftp' : {
        'debug' : True,
        'roots' : [
            {
                'id' : 'pdfid',
                'alias' : '127.0.0.1',
                'driver' : 'elfinder.volumes.storage.ElfinderVolumeStorage',
                'storageClass': 'elfinder.sftpstoragedriver.sftpstorage.SFTPStorage',
                'keepAlive' : True,
                'cache' : 300,
                #'uploadMaxSize' : '1024m',
            } 
        ]  
    },    
}

ELFINDER_CONNECTOR_OPTION_SETS.update(getattr(settings, 'ELFINDER_CONNECTOR_OPTION_SETS', {}))
