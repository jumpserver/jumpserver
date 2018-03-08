import os, re, time, urllib
from django.utils.translation import ugettext as _
from exceptions import ElfinderErrorMessages, VolumeNotFoundError, DirNotFoundError, FileNotFoundError, NamedError, NotAnImageError
from utils.volumes import instantiate_driver
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
from collections import defaultdict

class ElfinderConnector:
    """
    A python implementation of the 
    `elfinder connector api v2.1  <https://github.com/Studio-42/elFinder/wiki/Client-Server-API-2.1>`_. At the moment, it supports all elfinder commands except from ``netDrivers``.
    """

    _version = '2.1'
    _commit = 'b0144a0'
    _netDrivers = {}
    _commands = {
        'open' : { 'target' : False, 'tree' : False, 'init' : False, 'mimes' : False },
        'ls' : { 'target' : True, 'mimes' : False },
        'tree' : { 'target' : True },
        'parents' : { 'target' : True },
        'tmb' : { 'targets' : True },
        'file' : { 'target' : True, 'download' : False, 'request' : False },
        'size' : { 'targets' : True },
        'mkdir' : { 'target' : True, 'name' : True },
        'mkfile' : { 'target' : True, 'name' : True, 'mimes' : False },
        'rm' : { 'targets' : True },
        'rename' : { 'target' : True, 'name' : True, 'mimes' : False },
        'duplicate' : { 'targets' : True },
        'paste' : { 'dst' : True, 'targets' : True, 'cut' : False, 'mimes' : False },
        'upload' : { 'target' : True, 'FILES' : True, 'mimes' : False, 'html' : False, 'upload_path': False,
                     'chunk_name': False, 'is_first_chunk': False},
        'get' : { 'target' : True },
        'put' : { 'target' : True, 'content' : '', 'mimes' : False },
        'archive' : { 'targets' : True, 'type_' : True, 'mimes' : False },
        'extract' : { 'target' : True, 'mimes' : False },
        'search' : { 'q' : True, 'mimes' : False },
        'info' : { 'targets' : True, 'options': False },
        'dim' : { 'target' : True },
        'resize' : {'target' : True, 'width' : True, 'height' : True, 'mode' : False, 'x' : False, 'y' : False, 'degree' : False },
        #TODO: implement netmount
        'netmount'  : { 'protocol' : True, 'host' : True, 'path' : False, 'port' : False, 'user' : True, 'pass' : True, 'alias' : False, 'options' : False}
    }

    def __init__(self, opts, u_id, session = None):

        if not 'roots' in opts:
            opts['roots'] = []

        self._volumes = {}
        self._default = None
        self._loaded = False
        self._session = session
        self._time =  time.time()
        self._debug = 'debug' in opts and opts['debug'] 
        self._uploadDebug = ''
        self._mountErrors = []
        self.u_id = u_id
        
        #TODO: Use signals instead of the original connector's binding mechanism

        #for root in self.getNetVolumes():
        #    opts['roots'].append(root)
        for o in opts['roots'][self.u_id]:
            try:
                volume = instantiate_driver(o)
            except Exception as e:
                self._mountErrors.append(e.__unicode__())
                continue

            id_ = volume.id()
            self._volumes[id_] = volume

            if not self._default and volume.is_readable():
                self._default = self._volumes[id_]

        self._loaded = (self._default is not None)
    
    def loaded(self):
        """
        Check if the volume driver is loaded
        """
        return self._loaded

    def version(self, commit=False):
        """
        Get api version. The commit number refers to the corresponding official elfinder github commit number.
        """
        return '%s - %s' % (self._version, self._commit) if commit else self._version
    
    def commandExists(self, cmd):
        """
        Check if command exists
        """
        return cmd in self._commands and hasattr(self, '_%s' % cmd) and callable(getattr(self, '_%s' % cmd))
    
    def commandArgsList(self, cmd):
        """
        Return command required arguments info
        """
        return self._commands[cmd] if self.commandExists(cmd) else {}
    
    #def getNetVolumes(self):
    #    """
    #    Return  network volumes config.
    #    """
    #    return self._session.get('elFinderNetVolumes', []) if  self._session else []
        
    #def setNetVolumes(self, volumes):
    #    """
    #    Save network volumes config.
    #    """
    #    self._session['elFinderNetVolumes'] = volumes

    def error(self, *args):
        """
        Normalize error messages
        """
        errors = []
        for msg in args:
            if not isinstance(msg, basestring):
                errors += msg
            else:
                errors.append(msg)
        
        if not errors:
            return [ElfinderErrorMessages.ERROR_UNKNOWN,]
        return errors
    
    def execute(self, cmd, **kwargs):
        """
        Exec command and return result
        """
        if not self._loaded:
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_CONF, ElfinderErrorMessages.ERROR_CONF_NO_VOL)}
        
        if not self.commandExists(cmd):
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_UNKNOWN_CMD, cmd)}
        
        #check all required arguments are provided
        for arg, req in self.commandArgsList(cmd).items():
            if req and (not arg in kwargs or not kwargs[arg]):
                return {'error' : self.error(ElfinderErrorMessages.ERROR_INV_PARAMS, cmd)}
        
        #set mimes filter and pop mimes from the arguments list
        if 'mimes' in kwargs:
            for id_ in self._volumes:
                self._volumes[id_].set_mimes_filter(kwargs['mimes'])
            kwargs.pop('mimes')

        debug = self._debug or ('debug' in kwargs and int(kwargs['debug']))
        #remove debug kewyord argument  
        if 'debug' in kwargs:
            kwargs.pop('debug')
        result = getattr(self, '_%s' % cmd)(**kwargs)
        
        #checked for removed items as these are not directly returned
        if 'removed' in result:
            for id_ in self._volumes:
                result['removed'] += self._volumes[id_].removed()
                self._volumes[id_].reset_removed()
            #replace removed files info with removed files hashes and filter out duplicates
            result['removed'] = list(set([f['hash'] for f in result['removed']]))
        
        #call handlers for this command
        #TODO: a signal must be sent here
        
        if debug:
            result['debug'] = {
                'connector' : 'yawd-elfinder',
                'time' : time.time() - self._time,
                'upload' : self._uploadDebug,
                'volumes' : [v.debug() for v in self._volumes.values()],
                'mountErrors' : self._mountErrors
            }
        return result

    def _open(self, target='', init=False, tree=False):
        """
        **Command**: Open a directory
        
        Return:
            An array with following elements:
                :cwd:          opened directory information
                :options:      the volume options
                :files:        opened directory content [and dirs tree if 'tree' argument is ``True``]
                :api:          api version (if 'init' argument is ``True``)
                :uplMaxSize:   The maximum allowed upload size (if 'init' argument is ``True``)
                :error:        on failed
                
        This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """

        if isinstance(init, basestring):
            init = int(init)
            
        if isinstance(tree, basestring):
            tree = int(tree)

        if not init and not target:
            return {'error' : self.error(ElfinderErrorMessages.ERROR_INV_PARAMS, 'open')}

        #display name for use in error messages
        display_hash = 'default folder' if init else '#%s' % target

        #detect volume
        try:
            volume = self._volume(target)
        except VolumeNotFoundError as e:
            if not init:
                return {'error' : self.error(ElfinderErrorMessages.ERROR_OPEN, display_hash, e)}
            else:
                #on init request we can get invalid dir hash -
                #dir which can not be opened now, but remembered by client,
                #so open default volume
                volume = self._default
        
        try:
            cwd = volume.dir(hash_=target, resolve_link=True)
            if not cwd['read'] and init:
                try:
                    cwd = volume.dir(hash_=volume.default_path(), resolve_link=True)
                except (DirNotFoundError, FileNotFoundError) as e:
                    return {'error' : self.error(ElfinderErrorMessages.ERROR_OPEN, display_hash, e)}
        except (DirNotFoundError, FileNotFoundError) as e:
            if init:
                cwd = volume.dir(hash_=volume.default_path(), resolve_link=True)
            else:
                return {'error' : self.error(ElfinderErrorMessages.ERROR_OPEN, display_hash, e)}

        if not cwd['read']:
            return {'error' : self.error(ElfinderErrorMessages.ERROR_OPEN, display_hash, ElfinderErrorMessages.ERROR_PERM_DENIED)}

        files = []
        #get folder trees
        if tree:
            for id_ in self._volumes:
                files += self._volumes[id_].tree(exclude=target)
        
        #get current working directory files list and add to files if not already present
        try:
            ls = volume.scandir(cwd['hash'])
        except Exception as e:
            return {'error' : self.error(ElfinderErrorMessages.ERROR_OPEN, cwd['name'], e)}
        
        for file_ in ls:
            if not file_ in files:
                files.append(file_)

        result = {
            'cwd' : cwd,
            'options' : volume.options(cwd['hash']),
            'files' : files
        }

        if init:
            result['api'] = self._version
            result['netDrivers'] = self._netDrivers.keys()
            result['uplMaxSize'] = volume.upload_max_size()
        
        return result

    def _ls(self, target):
        """
        **Command**: Return a directory's file list. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        try:
            return { 'list' : self._volume(target).ls(target) }
        except:
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_OPEN, '#%s' % target) }

    def _tree(self, target):
        """
        **Command**: Return subdirs for required directory. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        try:
            return { 'tree' : self._volume(target).tree(target) }
        except:
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_OPEN, '#%s' % target) }
    
    def _parents(self, target):
        """
        **Command**: Return parents dir for required directory. this method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        try:
            return {'tree' : self._volume(target).parents(target) }
        except:
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_OPEN, u'#%s' % target) }

    def _tmb(self, targets):
        """
        **Command**: Return new automatically-created thumbnails list. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        result  = { 'images' : {} }
        for target in targets:
            try:
                thumb = self._volume(target).tmb(target)
                if thumb:
                    result['images'][target] = thumb  
            except (VolumeNotFoundError, NotAnImageError):
                continue

        return result
    
    def _file(self, target, request=None, download=False):
        """
        **Command**: Get a file
        
        Required to output file in browser when volume URL is not set.
        Used to download the file as well.
        
        Return:
            An array containing an opened file pointer, the root itself and the required response headers
            
        This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        
        if isinstance(download, basestring):
            download = int(download)
        
        try:
            volume = self._volume(target)
            file_ = volume.file(target)
        except (VolumeNotFoundError, FileNotFoundError): 
            return { 'error' : _('File not found'), 'header' : { 'Status' : 404 }, 'raw' : True }
        
        if not file_['read']:
            return { 'error' : _('Access denied'), 'header' : { 'Status' : 403 }, 'raw' : True }
        
        try:
            fp = volume.open(target)
        except os.error: #Normally this could raise a FileNotFoundError as well, but we already checked this
            return { 'error' : _('File not found'), 'header' : { 'Status' : 404 }, 'raw' : True }

        if download:
            disp = 'attachment'
            mime = 'application/octet-stream'
        else:
            disp  = 'inline' if re.match('(image|text)', file_['mime'], re.IGNORECASE) or file_['mime'] == 'application/x-shockwave-flash' else 'attachment'  
            mime = file_['mime']

        filenameEncoded = urllib.quote(file_['name'].encode('utf-8')) #unicode filename support
        if not '%' in filenameEncoded: #ASCII only
            filename = 'filename="%s"' % file_['name']
        elif request and hasattr(request, 'META') and 'HTTP_USER_AGENT' in request.META:
            ua = request.META['HTTP_USER_AGENT']
            if re.search('MSIE [4-8]', ua): #IE < 9 do not support RFC 6266 (RFC 2231/RFC 5987)
                filename = 'filename="%s"' % filenameEncoded
            elif not 'Chrome'in ua and 'Safari' in ua: # Safari
                filename = 'filename="%s"' % file_['name'].replace('"','')
            else: #RFC 6266 (RFC 2231/RFC 5987)
                filename = "filename*=UTF-8''%s" % filenameEncoded
        else:
            filename = ''

        result = {
            'volume' : volume,
            'pointer' : fp,
            'info' : file_,
            'header' : {
                'Content-Type' : mime, 
                'Content-Disposition' : '%s; %s' % (disp, filename),
                'Content-Location' : file_['name'].encode('utf-8'),  #unicode filename support
                'Content-Transfer-Encoding' : 'binary',
                'Content-Length' : file_['size'],
                #'Connection' : 'close'
            }
        }

        return result

    def _size(self, targets):
        """
        **Command**: Count total file size of all directories in ``targets`` param.
        
        This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        size = 0
        
        for target in targets:
            try:
                volume = self._volume(target)
                file_ = volume.file(target)
            except (VolumeNotFoundError, FileNotFoundError):
                file_ = { 'read' : 0 }
                
            if not file_['read']:
                return { 'error' : self.error(ElfinderErrorMessages.ERROR_OPEN, u'#%s' % target) }
            
            size += volume.size(target)

        return { 'size' : size }

    def _mkdir(self, target, name):
        """
        **Command**: Create a new directory. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        try:
            volume = self._volume(target)
        except VolumeNotFoundError:
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_MKDIR, name, ElfinderErrorMessages.ERROR_TRGDIR_NOT_FOUND, '#%s' % target)}
        try:
            result = {'added': []}
            for dirs in name:
                try:
                    if str(dirs).startswith('/'):
                        dirs = dirs[1:]
                    dir_ = volume.mkdir(target, dirs)
                    result['added'].append(dir_)
                except Exception, e:
                    result['warning'] = self.error(ElfinderErrorMessages.ERROR_UPLOAD_FILE, dirs, e)
            return result
        except NamedError as e:
            return { 'error' : self.error(e, e.name, ElfinderErrorMessages.ERROR_MKDIR) }
        except Exception as e:
            return { 'error': self.error(ElfinderErrorMessages.ERROR_MKDIR, name, e) }

    def _mkfile(self, target, name):
        """
        **Command**: Create a new, empty file. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        try:
            volume = self._volume(target)
        except VolumeNotFoundError:
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_MKFILE, name, ElfinderErrorMessages.ERROR_TRGDIR_NOT_FOUND, '#%s' % target)}

        try:
            return { 'added' : [volume.mkfile(target, name)] }
        except NamedError as e:
            return { 'error' : self.error(e, e.name, ElfinderErrorMessages.ERROR_MKFILE, name ) }
        except Exception as e:
            return { 'error': self.error(ElfinderErrorMessages.ERROR_MKFILE, name, e) }

    def _rename(self, target, name):
        """
        **Command**: Rename a file. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        try:
            volume = self._volume(target)
        except (VolumeNotFoundError):
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_RENAME, '#%s' % target, ElfinderErrorMessages.ERROR_FILE_NOT_FOUND) }

        try:
            return { 'added' : [volume.rename(target, name)], 'removed' : volume.removed() }
        except NamedError as e:
            return { 'error' : self.error(e, e.name, ElfinderErrorMessages.ERROR_RENAME) }
        except FileNotFoundError:
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_RENAME, '#%s' % target, ElfinderErrorMessages.ERROR_FILE_NOT_FOUND) }
        except Exception as e:
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_RENAME, e) }

    def _duplicate(self, targets, suffix='copy'):
        """
        **Command**: Duplicate a file. Create a copy with "{suffix} %d" suffix,
        where "%d" is an integer and ``suffix`` an argument that defaults to `'copy`'.
        
        This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used. 
        """
        result = { 'added' : [] }
        
        for target in targets:
            try:
                volume = self._volume(target)
                volume.file(target)
            except (VolumeNotFoundError, FileNotFoundError):
                result['warning'] = self.error(ElfinderErrorMessages.ERROR_COPY, u'#%s' % target, ElfinderErrorMessages.ERROR_FILE_NOT_FOUND)
                continue
            
            try:
                result['added'].append(volume.duplicate(target, suffix))
            except Exception as e:
                result['warning'] = self.error(e)
        
        return result
    
    def _rm(self, targets):
        """
        **Command**: Remove directories or files. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        result  = {'removed' : []}

        for target in targets:
            try:
                volume = self._volume(target)
            except VolumeNotFoundError:
                result['warning'] = self.error(ElfinderErrorMessages.ERROR_RM, '#%s' % target, ElfinderErrorMessages.ERROR_FILE_NOT_FOUND)
                continue

            try:
                volume.rm(target)
            except NamedError as e:
                result['warning'] = self.error(e, e.name)
            except Exception as e:
                result['warning'] = self.error(e)

        return result
    
    def _upload(self, target, FILES, html=False, upload_path=False, chunk_name=False, is_first_chunk=False):
        """
        **Command**: Save uploaded files. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        if isinstance(html, basestring):
            html = int(html)
        
        header = { 'Content-Type' : 'text/html; charset=utf-8' } if html else {}
        result = { 'added' : [], 'header' : header }
        try:
            files = FILES.getlist('upload[]')
        except KeyError:
            files = []
        if not isinstance(files, list) or not files:
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_UPLOAD, ElfinderErrorMessages.ERROR_UPLOAD_NO_FILES), 'header' : header }

        try:
            volume = self._volume(target)
        except VolumeNotFoundError:
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_UPLOAD, ElfinderErrorMessages.ERROR_TRGDIR_NOT_FOUND, '#%s' % target), 'header' : header }
        if not upload_path:  # not is directory
            for uploaded_file in files:
                try:
                    file_ = volume.upload(uploaded_file, target, chunk_name, is_first_chunk)
                    result['added'].append(file_)
                except Exception, e:
                    result['warning'] = self.error(ElfinderErrorMessages.ERROR_UPLOAD_FILE, uploaded_file.name, e)
                    self._uploadDebug = 'Upload error: Django handler error'
        else:  # directory
            try:
                all_ = defaultdict(list)
                for key, value in [(v, i) for i, v in enumerate(upload_path)]:  # upload directory list
                    if key.startswith('/'):
                        key = (os.path.split(key[1:]))[0]  # get path
                    all_[key].append(value)
            except Exception as e:
                return {'error': 'get directory error, %s' % e, 'header': header}
            for item in all_.keys():
                real_path = "%s/%s" % (volume.decode(target), item)  # get real path
                new_target = volume.encode(real_path)  # get new target
                try:
                    volume = self._volume(new_target)  # get volume object
                except VolumeNotFoundError:
                    return {'error': self.error(ElfinderErrorMessages.ERROR_UPLOAD,
                                                ElfinderErrorMessages.ERROR_TRGDIR_NOT_FOUND, '#%s' % new_target),
                            'header': header}
                for file_index in all_[item]:
                    try:
                        file_ = volume.upload(files[file_index], new_target, chunk_name, is_first_chunk)
                        result['added'].append(file_)
                    except Exception, e:
                        result['warning'] = self.error(ElfinderErrorMessages.ERROR_UPLOAD_FILE, uploaded_file.name, e)
                        self._uploadDebug = 'Upload error: Django handler error'
        return result


    def _paste(self, targets, dst, cut=False):
        """
        **Command**: Copy/move ``targets`` files into a new destination ``dst``.
        
        This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        
        if isinstance(cut, basestring):
            cut = int(cut)

        error = ElfinderErrorMessages.ERROR_MOVE if cut else ElfinderErrorMessages.ERROR_COPY
        result = { 'added' : [], 'removed' : [] }
        
        try:
            dstVolume = self._volume(dst)
        except VolumeNotFoundError:
            return { 'error' : self.error(error, u'#%s' % targets[0], ElfinderErrorMessages.ERROR_TRGDIR_NOT_FOUND, u'#%s' % dst) }
        
        for target in targets:
            try:
                srcVolume = self._volume(target)
            except VolumeNotFoundError:
                result['warning'] = self.error(error, u'#%s' % target, ElfinderErrorMessages.ERROR_FILE_NOT_FOUND)
                continue

            try:
                result['added'].append(dstVolume.paste(srcVolume, target, dst, cut))
            except NamedError as e:
                result['warning'] = self.error(e, e.name)
            except Exception as e:
                result['warning'] = self.error(e)

        return result

    def _get(self, target):
        """
        **Command**: Return file contents. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """        
        try:
            volume = self._volume(target)
            volume.file(target)
        except (VolumeNotFoundError, FileNotFoundError):
            return {'error' : self.error(ElfinderErrorMessages.ERROR_OPEN, u'#%s' % target, ElfinderErrorMessages.ERROR_FILE_NOT_FOUND)}
        
        try:
            content = volume.get_contents(target)
        except Exception as e:
            return {'error' : self.error(ElfinderErrorMessages.ERROR_OPEN, volume.path(target), e)}
        
        #the content will be returned as json, so try to json encode it
        #throw an error if it cannot be properly serialized
        try:
            import json
            json.dumps(content)
        except:
            return {'error' : self.error(ElfinderErrorMessages.ERROR_NOT_UTF8_CONTENT, volume.path(target))}
        
        return {'content' : content }

    def _put(self, target, content):
        """
       **Command**:  Save ``content`` into a text file. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        try:
            volume = self._volume(target)
            volume.file(target)
        except (VolumeNotFoundError, FileNotFoundError):
            return {'error' : self.error(ElfinderErrorMessages.ERROR_SAVE, u'#%s' % target, ElfinderErrorMessages.ERROR_FILE_NOT_FOUND)}
        
        try:
            return {'changed' : [volume.put_contents(target, content)]} 
        except Exception as e:
            return {'error' : self.error(ElfinderErrorMessages.ERROR_SAVE, volume.path(target), e)}

    def _extract(self, target):
        """
        **Command**:  Extract files from archive. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """

        try:
            volume = self._volume(target)
            volume.file(target)
        except (VolumeNotFoundError, FileNotFoundError):
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_EXTRACT, u'#%s' % target, ElfinderErrorMessages.ERROR_FILE_NOT_FOUND) }

        try:
            return {'added' : [volume.extract(target)] }
        except Exception as e:
            return {'error' : self.error(ElfinderErrorMessages.ERROR_EXTRACT, volume.path(target), e)}

    def _archive(self, targets, type_):
        """
        **Command**: Create a new archive file containing all files in
        ``targets`` param. 
        
        This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """

        try:
            volume = self._volume(targets[0])
        except:
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_ARCHIVE, ElfinderErrorMessages.ERROR_TRGDIR_NOT_FOUND) }
    
        try:
            return {'added' : [volume.archive(targets, type_)]}
        except Exception as e:
            return {'error' : self.error(ElfinderErrorMessages.ERROR_ARCHIVE, e)}

    def _search(self, q):
        """
        **Command**: Search files for ``q``. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        q = q.strip()
        result = []
        for volume in self._volumes.values():
            result += volume.search(q)
        return {'files' : result}

    def _info(self, targets, options=False):
        """
        **Command**: Return file info (used by client "places" ui). This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        
        if isinstance(options, basestring):
            options = int(options)
        
        files = []
        for hash_ in targets:
            try:
                volume = self._volume(hash_)
                if options:
                    options = volume.options(hash_)
                    options.update(volume.file(hash_))
                    files.append(options)
                else:
                    files.append(volume.file(hash_))
            except:
                continue

        return {'files' : files}

    def _dim(self, target):
        """
        **Command**: Return image dimensions. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """        
        try:
            return { 'dim' : self._volume(target).dimensions(target) }
        except (VolumeNotFoundError, FileNotFoundError, NotAnImageError):
            return {}

    def _resize(self, target, width, height, mode=None, x='0', y='0', degree='0'):
        """
        **Command**: Resize ``target`` image. This method should not be invoked 
        directly, the :meth:`elfinder.connector.ElfinderConnector.execute`
        method must be used.
        """
        width, height, x, y, degree = int(width), int(height), int(x), int(y), int(degree)
        bg = ''

        try:
            volume = self._volume(target)
            volume.file(target)
        except (VolumeNotFoundError, FileNotFoundError):
            return { 'error' : self.error(ElfinderErrorMessages.ERROR_RESIZE, '#%s' % target, ElfinderErrorMessages.ERROR_FILE_NOT_FOUND) }
        
        try:
            return { 'changed' : [volume.resize(target, width, height, x, y, mode, bg, degree)]}
        except Exception as e:
            return {'error' : self.error(ElfinderErrorMessages.ERROR_RESIZE, volume.path(target), e)}

    def _volume(self, hash_):
        """
        Return root - file's owner
        """
        if hash_:
            for id_, v in self._volumes.items():
                if hash_.find(id_) == 0:
                    return v
        raise VolumeNotFoundError()
