import os
from django.conf import settings
from django.utils import unittest
from elfinder.conf import settings as ls
from elfinder.connector import ElfinderConnector
from elfinder.exceptions import ElfinderErrorMessages

class ConnectorInitTestCase(unittest.TestCase):
    
    def setUp(self):
        settings.MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media') 
    
    def test_init(self):
        """
        Test the ElfinderConnector __init__ method
        """
        #fault-tolerant initialization
        connector = ElfinderConnector({})
        self.assertEqual(connector.loaded(), False)
        
        connector = ElfinderConnector({})
        self.assertEqual(connector.loaded(), False)
        
        #initialize with 'default' optionset
        connector = ElfinderConnector(ls.ELFINDER_CONNECTOR_OPTION_SETS['default'])
        self.assertEqual(connector.loaded(), True)
        
    def test_execute(self):
        """
        Test the execute method.
        """
        
        #test invalid configuration
        connector = ElfinderConnector({})
        self.assertEqual(ElfinderErrorMessages.ERROR_CONF in connector.execute('open')['error'], True)
        
        connector = ElfinderConnector(ls.ELFINDER_CONNECTOR_OPTION_SETS['default'])
        #test invalid command
        self.assertEqual(ElfinderErrorMessages.ERROR_UNKNOWN_CMD in connector.execute('dummy')['error'], True)
        #test missing arguments
        self.assertEqual(ElfinderErrorMessages.ERROR_INV_PARAMS in connector.execute('ls')['error'], True)
        #test it is actually doing something
        self.assertEqual('error' in connector.execute('open', mimes=['image'], init=True), False)
        #test debug keyword
        self.assertEqual('debug' in connector.execute('open', init=True), False)
        self.assertEqual('debug' in connector.execute('open', init=True, debug=True), True)

class ConnectorEVLFOpen(unittest.TestCase):
    """
    Test that open command is implemented and behaves as expected. It also checks the response's conformance with
    the `elfinder 2.1 Server API specification <https://github.com/Studio-42/elFinder/wiki/Client-Server-API-2.1>`_
    """
    
    def setUp(self):
        settings.MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media')
        
        self.opts = ls.ELFINDER_CONNECTOR_OPTION_SETS['default'].copy()
        self.opts['roots'][0]['path'] = settings.MEDIA_ROOT
        self.opts['roots'][0]['URL'] = settings.MEDIA_URL
        
        self.maxDiff = None

    def test_open_specs(self):
        """
        Test the command compiles to the API specification
        """
        
        connector = ElfinderConnector(self.opts)

        #command accepts the specification arguments
        argslist = connector.commandArgsList('open')
        self.assertIn('target', argslist)
        self.assertIn('init', argslist)
        self.assertIn('tree', argslist)
        self.assertIn('mimes', argslist)
        
        #test invalid keyword arguments
        self.assertEqual(ElfinderErrorMessages.ERROR_INV_PARAMS in connector.execute('open')['error'], True)
        
        #test invalid target
        self.assertEqual(ElfinderErrorMessages.ERROR_OPEN in connector.execute('open', target='dummy')['error'], True)
    
    def test_open_default(self):
        """
        Test the default optionset
        """
        
        connector = ElfinderConnector(self.opts)
        
        #************ init without tree ***********
        ret = connector.execute('open', target='dummy', init='1')

        #check files and cwd
        self.assertEqual(len(ret['files']), 2)
        self.assertNotEqual(ret['files'][0]['hash'], ret['files'][1]['hash'])
        self.assertEqual(ret['files'][0]['name'], 'files')
        self.assertEqual(ret['files'][1]['name'], 'test')
        self.assertEqual(ret['cwd']['dirs'], 1)
        self.assertEqual(ret['cwd']['name'], connector._default._root_name)
        self.assertEqual(ret['cwd']['read'], 1)
        self.assertEqual(ret['cwd']['write'], 1)
        self.assertEqual(ret['cwd']['locked'], 1)
        self.assertEqual(ret['cwd']['hidden'], 0)
        self.assertEqual(ret['cwd']['size'], 'unknown')
        self.assertEqual(ret['cwd']['mime'], 'directory')
        self.assertEqual(ret['cwd']['volumeid'], 'llff_')
        self.assertIsInstance(ret['cwd']['ts'], float)
        self.assertNotIn('phash', ret['cwd'])
        self.assertGreater(len(ret['cwd']['hash']), 0)
        
        #other response attributes
        self.assertNotIn('error', ret)
        self.assertIn('netDrivers', ret)
        self.assertEqual(ret['uplMaxSize'], 128 * 1048576)
        self.assertEqual(ret['api'], '2.1')
        self.assertEqual(ret['options']['pathUrl'], settings.MEDIA_URL)
        self.assertEqual(ret['options']['tmbUrl'], '%s.tmb/' % settings.MEDIA_URL)
        self.assertIn('create', ret['options']['archivers'])
        self.assertIn('extract', ret['options']['archivers'])
        self.assertEqual(ret['options']['disabled'], [])
        self.assertEqual(ret['options']['copyOverwrite'], 1)
        self.assertEqual(ret['options']['separator'], os.sep)
        self.assertEqual(ret['options']['path'], connector._default._root_name)
        
        
        #********* init with tree ***********
        ret_tree = connector.execute('open', target='dummy', init='1', tree='1')
        self.check_root_tree(ret_tree, 3, connector._default._root_name)
        
        ret['files'][:0] = [ret['cwd']]
        self.assertEqual(ret, ret_tree)
        
        #******** init with tree and debug *******
        ret_tree_debug = connector.execute('open', target='dummy', init='1', tree='1', debug='1')
        
        self.assertEqual(ret_tree_debug['debug']['connector'], 'yawd-elfinder')
        self.assertEqual(ret_tree_debug['debug']['mountErrors'], [])
        self.assertEqual(ret_tree_debug['debug']['upload'], '')
        self.assertEqual(ret_tree_debug['debug']['volumes'], [{'id': 'llff_', 'name': 'localfilesystem'}])
        self.assertIsInstance(ret_tree_debug['debug']['time'], float)
        
        del ret_tree_debug['debug']
        self.assertEqual(ret_tree, ret_tree_debug)
        
    def test_open_startpath(self):
        """
        Test startpath option
        """
        
        self.opts['roots'][0]['startPath'] = 'files'
        connector = ElfinderConnector(self.opts)
        
        #************ init without tree ***********
        ret = connector.execute('open', target='dummy', init='1')

        #check files and cwd
        self.assertEqual(len(ret['files']), 2)
        self.assertNotEqual(ret['files'][0]['hash'], ret['files'][1]['hash'])
        self.assertEqual(ret['files'][0]['name'], '2bytes.txt')
        self.assertEqual(ret['files'][1]['name'], 'directory')
        self.assertEqual(ret['cwd']['dirs'], 1)
        self.assertEqual(ret['cwd']['name'], 'files')
        self.assertEqual(ret['cwd']['read'], 1)
        self.assertEqual(ret['cwd']['write'], 1)
        self.assertEqual(ret['cwd']['locked'], 0)
        self.assertEqual(ret['cwd']['hidden'], 0)
        self.assertEqual(ret['cwd']['size'], 'unknown')
        self.assertEqual(ret['cwd']['mime'], 'directory')
        self.assertNotIn('volumeid', ret['cwd'])
        self.assertIsInstance(ret['cwd']['ts'], float)
        self.assertGreater(len(ret['cwd']['phash']), 0)
        self.assertGreater(len(ret['cwd']['hash']), 0)
        
        #other response attributes
        self.assertNotIn('error', ret)
        self.assertIn('netDrivers', ret)
        self.assertEqual(ret['uplMaxSize'], 128 * 1048576)
        self.assertEqual(ret['api'], '2.1')
        self.assertEqual(ret['options']['pathUrl'], '%sfiles' % settings.MEDIA_URL)
        self.assertEqual(ret['options']['tmbUrl'], '%s.tmb/' % settings.MEDIA_URL)
        self.assertIn('create', ret['options']['archivers'])
        self.assertIn('extract', ret['options']['archivers'])
        self.assertEqual(ret['options']['disabled'], [])
        self.assertEqual(ret['options']['copyOverwrite'], 1)
        self.assertEqual(ret['options']['separator'], os.sep)
        self.assertEqual(ret['options']['path'], '%s%sfiles' % (connector._default._root_name, os.sep))
        
        #********* init with tree ***********
        ret_tree = connector.execute('open', target='dummy', init='1', tree='1')
        self.check_root_tree(ret_tree, 5, connector._default._root_name)

        #cleanup startpath
        self.opts['startpath'] = ''
        
    def test_open_path(self):
        
        connector = ElfinderConnector(self.opts)
        
        #************ init without tree ***********
        ret = connector.execute('open', target=connector._default.encode(
            connector._default._join_path(settings.MEDIA_ROOT, 
                connector._default._join_path('files', 'directory'))),
            init='1')

        #check files and cwd
        self.assertEqual(len(ret['files']), 1)
        self.assertEqual(ret['files'][0]['name'], 'yawd-logo.png')
        self.assertNotIn('dirs', ret['cwd'])
        self.assertEqual(ret['cwd']['name'], 'directory')
        self.assertEqual(ret['cwd']['read'], 1)
        self.assertEqual(ret['cwd']['write'], 1)
        self.assertEqual(ret['cwd']['locked'], 0)
        self.assertEqual(ret['cwd']['hidden'], 0)
        self.assertEqual(ret['cwd']['size'], 'unknown')
        self.assertEqual(ret['cwd']['mime'], 'directory')
        self.assertNotIn('volumeid', ret['cwd'])
        self.assertIsInstance(ret['cwd']['ts'], float)
        self.assertGreater(len(ret['cwd']['phash']), 0)
        self.assertGreater(len(ret['cwd']['hash']), 0)
        
        #other response attributes
        self.assertNotIn('error', ret)
        self.assertIn('netDrivers', ret)
        self.assertEqual(ret['uplMaxSize'], 128 * 1048576)
        self.assertEqual(ret['api'], '2.1')
        self.assertEqual(ret['options']['pathUrl'], '%sfiles/directory' % settings.MEDIA_URL)
        self.assertEqual(ret['options']['tmbUrl'], '%s.tmb/' % settings.MEDIA_URL)
        self.assertIn('create', ret['options']['archivers'])
        self.assertIn('extract', ret['options']['archivers'])
        self.assertEqual(ret['options']['disabled'], [])
        self.assertEqual(ret['options']['copyOverwrite'], 1)
        self.assertEqual(ret['options']['separator'], os.sep)
        self.assertEqual(ret['options']['path'], '%s%sfiles%sdirectory' % (connector._default._root_name, os.sep, os.sep))

        
    def check_root_tree(self, ret, len_, name):
        """
        Check that result contains the root tree
        """
        
        self.assertEqual(len(ret['files']), len_)
        self.assertEqual(ret['files'][0]['name'], name)
        self.assertEqual(ret['files'][1]['name'], 'files')
        self.assertEqual(ret['files'][2]['name'], 'test')
                        
        for i in range(1, len_):
            for j in range(i-1, -1, -1):
                self.assertNotEqual(ret['files'][i]['hash'], ret['files'][j]['hash'])
                self.assertNotEqual(ret['files'][i]['name'], ret['files'][j]['name'])
