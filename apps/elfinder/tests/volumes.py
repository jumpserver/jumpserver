import os, re
from django.conf import settings
from django.utils import unittest
from elfinder.volumes.filesystem import ElfinderVolumeLocalFileSystem
from elfinder.volumes.storage import ElfinderVolumeStorage

class ElfinderVolumeLocalFileSystemTestCase(unittest.TestCase):
    volume_class = ElfinderVolumeLocalFileSystem
    
    def setUp(self):
        settings.MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media')
    
        self.driver = self.volume_class()
        self.options = {
            'id' : 'lfTest1',
            'path' : settings.MEDIA_ROOT,
            'alias' : 'Elfinder files',
            'URL' : settings.MEDIA_URL,
            'uploadAllow' : ['all',],
            'uploadDeny' : ['all',],
            'uploadOrder' : ['deny', 'allow'],
            'attributes' : [
                    {
                        'pattern' : '^%(sep)sfiles%(sep)sdirectory' % {'sep' : os.sep},
                        'read' : True,
                        'write': True,
                        'hidden' : True,
                        'locked' : True
                    },
            ]
        }
            
        self.driver.mount(self.options)
        self.default_path = self.driver.default_path()
        self.realPath = self.driver.decode(self.default_path)
    
    def test_defaultpath(self):
        self.assertEqual(isinstance(self.default_path, basestring), True)
        self.assertEqual(len(self.default_path) > 0, True)
    
    def test_dir(self):
        
        root = self.driver.dir(self.default_path, False)
        self.assertEqual(root['read'], 1)
        self.assertEqual(root['write'], 1)
        self.assertEqual(root['mime'], 'directory')
        self.assertIn('volumeid', root)
        self.assertIn('ts', root)
        self.assertIn('name', root)
        self.assertIn('hash', root)
        self.assertIn('size', root)
        self.assertIn('locked', root)
        
    def test_stat_dir(self):
        stat = self.driver.stat(self.realPath)
        self.assertEqual(stat['size'], 'unknown')
        self.assertEqual(stat['mime'], 'directory')
        self.assertEqual(stat['read'], 1)
        self.assertEqual(stat['write'], 1)
        self.assertIsInstance(stat['ts'], float)
        self.assertEqual(stat['dirs'], 1)
        
    def test_stat_file(self):
        stat = self.driver.stat(self.driver._join_path(self.driver._options['path'], self.driver._join_path('files','2bytes.txt')))
        self.assertEqual(stat['name'], '2bytes.txt')
        self.assertEqual(stat['read'], 1)
        self.assertEqual(stat['write'], 1)
        self.assertEqual(stat['mime'].startswith('text/'), True)
        self.assertEqual(stat['size'], 2)
        self.assertEqual(stat['hash'], self.driver.encode(self.driver._join_path(self.options['path'], self.driver._join_path('files','2bytes.txt'))))
        self.assertEqual(stat['phash'], self.driver.encode(self.driver._join_path(self.options['path'],'files')))
        self.assertIsInstance(stat['ts'], float)
        self.assertNotIn('dirs', stat)
        
    def test_dimensions(self):
        dim = self.driver.dimensions(self.driver.encode(self.driver._join_path(self.driver._options['path'], self.driver._join_path('files', self.driver._join_path('directory', 'yawd-logo.png')))))
        self.assertEqual(dim, '260x35')
        
    def test_tree(self):
        tree = self.driver.tree(self.default_path, 2)
        self.assertEquals(len(tree), 3)
        self.assertEquals(tree[0]['hash'], self.default_path)
        self.assertEquals(tree[1]['hash'], self.driver.encode(self.driver._join_path(self.driver._options['path'],'files')))
        self.assertEquals(tree[2]['hash'], self.driver.encode(self.driver._join_path(self.driver._options['path'],'test')))
        
    def test_open_close(self):
        hash_ = self.driver.encode(self.driver._join_path(self.options['path'], self.driver._join_path('files','2bytes.txt')))
        fp = self.driver.open(hash_)
        self.assertEqual(fp.read(), '01')
        self.driver.close(fp, hash_)
        
    def test_mkfile_unlink(self):
        path = self.driver._join_path(self.options['path'], 'files')
        name = 'tmpfile'
        joined_path = self.driver._join_path(path, name)

        enc_path = self.driver.encode(path)
        enc_joined_path = self.driver.encode(joined_path)

        stat = self.driver.mkfile(enc_path, name)
        self.driver.rm(enc_joined_path)
        removed = self.driver.removed()
        
        self.assertEqual(stat['hash'], enc_joined_path)
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]['name'], name)
        self.assertEqual(removed[0]['hash'], enc_joined_path)
        self.assertEqual(removed[0]['phash'], enc_path)
        self.assertEqual(removed[0]['realpath'], joined_path)
        self.assertEqual(removed[0]['read'], 1)
        self.assertEqual(removed[0]['write'], 1)
        self.assertEqual(removed[0]['size'], 0)
        self.assertIn('mime', removed[0])
        self.assertIn('ts', removed[0])
        
    def test_mkdir_rmdir(self):
        path = self.driver._join_path(self.options['path'], 'files')
        name = 'tmpdir'
        joined_path = self.driver._join_path(path, name)

        enc_path = self.driver.encode(path)
        enc_joined_path = self.driver.encode(joined_path)

        stat = self.driver.mkdir(enc_path, name)
        self.driver.rm(enc_joined_path)
        removed = self.driver.removed()
        
        self.assertEqual(stat['hash'], enc_joined_path)
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]['name'], name)
        self.assertEqual(removed[0]['hash'], enc_joined_path)
        self.assertEqual(removed[0]['phash'], enc_path)
        self.assertEqual(removed[0]['realpath'], joined_path)
        self.assertEqual(removed[0]['read'], 1)
        self.assertEqual(removed[0]['write'], 1)
        self.assertEqual(removed[0]['size'], 'unknown')
        self.assertEqual(removed[0]['mime'], 'directory')
        self.assertIn('ts', removed[0])
        
    def test_locked(self):
        stat = self.driver.stat(self.driver._join_path(self.options['path'], self.driver._join_path('files', 'directory')))
        self.assertEqual(stat['locked'], 1)
        
        stat = self.driver.stat(self.driver._join_path(self.options['path'], 'files'))
        self.assertEqual(stat['locked'], 0)
        
    def test_hidden(self):
        stat = self.driver.stat(self.driver._join_path(self.options['path'], self.driver._join_path('files', 'directory')))
        self.assertEqual(stat['hidden'], 1)
        
        stat = self.driver.stat(self.driver._join_path(self.options['path'], 'files'))
        self.assertEqual(stat['hidden'], 0)
        
    def tearDown(self):
        self.driver.reset_removed()

class ElfinderVolumeLocalFileSystemThumbnailTestCase(unittest.TestCase):
    volume_class = ElfinderVolumeLocalFileSystem
    
    def setUp(self):
        settings.MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media')
        self.driver = self.volume_class()
        
        options = {
            'id' : 'test',
            'tmpPath' : self.driver._join_path(os.path.dirname(__file__), 'tmbtest'),
            'tmbURL' : 'http://example.com/files', #test _urlize
            'tmbSize' : 32
        }

        self.driver.mount(options)
        self.default_path = self.driver.default_path()
        self.realPath = self.driver.decode(self.default_path)
        
    def test_options(self):
        
        options = self.driver.options(self.default_path)
        self.assertEqual(options['tmbUrl'], 'http://example.com/files/')
        self.assertEqual(options['separator'], os.sep)
        self.assertEqual(options['path'].startswith(settings.MEDIA_ROOT), False)
        self.assertIn('url', options)
        self.assertIn('archivers', options)
        self.assertIn('disabled', options)
        self.assertIn('copyOverwrite', options)

class ElfinderVolumeStorageTestCase(ElfinderVolumeLocalFileSystemTestCase):
    volume_class = ElfinderVolumeStorage
    
    def test_tree(self):
        tree = self.driver.tree(self.default_path, 2)
        self.assertEquals(len(tree), 3)
        self.assertEquals(tree[0]['hash'], self.default_path)
        self.assertEquals(tree[1]['hash'], self.driver.encode(self.driver._join_path(self.driver._options['path'],'files')))
        self.assertEquals(tree[2]['hash'], self.driver.encode(self.driver._join_path(self.driver._options['path'],'test')))

class ElfinderVolumeFilePermissionTestcase(unittest.TestCase):
    
    def setUp(self):
        
        options = {
            'id' : 'stTest1',
            'attributes' : [{
                'pattern' : r'a%stmp' % re.escape(os.sep),
                'read' : True,
                'write' : False,
                'locked' : True,
                'hidden' : True,
            },{
                'pattern' : r'tmp',
                'read' : False,
                'write' : False,
                'locked' : True,
                'hidden' : True,
            }],
            'defaults' : {
                'read' : False
            }
        }

        self.driver = ElfinderVolumeLocalFileSystem()
        self.driver.mount(options)
        self.root = self.driver.decode(self.driver.default_path())
    
    def test_read(self):
        
        self.assertEqual(self.driver._attr('%(root)s%(sep)sa%(sep)sb%(sep)sc' % {'root':  self.root, 'sep':os.sep}, 'read'), False)
        self.assertEqual(self.driver._attr('%(root)s%(sep)sa%(sep)stmp%(sep)sc' % {'root': self.root, 'sep':os.sep}, 'read'), True)
        self.assertEqual(self.driver._attr('%(root)s%(sep)sb%(sep)stmp%(sep)sc' % {'root': self.root, 'sep':os.sep}, 'read'), False)
    
    def test_locked(self):
        
        self.assertEqual(self.driver._attr(self.root, 'locked'), True)