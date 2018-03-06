import json
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.forms.widgets import Input
from django.utils.safestring import mark_safe
from django.utils.translation import to_locale, get_language, ugettext as _
from fields import ElfinderFile
from conf import settings as ls

class ElfinderWidget(Input):    
    """
    A widget that opens the elfinder file manager for selecting a file.
    ``attrs``
        The TextInput attrs
    ``options``
        Optional. Sets the elfinder (client) configuration options
    ``optionset``
        The key of the ELFINDER_CONNECTOR_OPTION_SETS setting to use as connector settings 
    """
    input_type = ''
    
    def __init__(self, optionset, start_path, attrs={'size':'42'}, options={}):
        
        self.options, self.optionset, self.start_path = options, optionset, start_path
        super(ElfinderWidget, self).__init__(attrs)
        
        #locate current locale
        self.current_locale = to_locale(get_language()) 
        
    def _media(self):
        """
        Set the widget's javascript and css
        """
        js = [ls.ELFINDER_JS_URLS[x] for x in sorted(ls.ELFINDER_JS_URLS)] + [ls.ELFINDER_WIDGET_JS_URL]
        screen_css = [ls.ELFINDER_CSS_URLS[x] for x in sorted(ls.ELFINDER_CSS_URLS)] + [ls.ELFINDER_WIDGET_CSS_URL]

        #add language file to javascript media
        if not self.current_locale.startswith('en') and self.current_locale in ls.ELFINDER_LANGUAGES:
            js.append('%selfinder.%s.js' % (ls.ELFINDER_LANGUAGES_ROOT_URL, self.current_locale))
        
        return forms.Media(css= {'screen': screen_css}, js = js)

    media = property(_media)
    
    def render(self, name, value, attrs=None):
        """
        Display the widget
        """
        #if self.optionset in ls.ELFINDER_CONNECTOR_OPTION_SETS and 'uploadAllow' in ls.ELFINDER_CONNECTOR_OPTION_SETS[self.optionset] and ls.ELFINDER_CONNECTOR_OPTION_SETS[self.optionset]['uploadAllow']:
        #    html = '<div class="elfinder_filetypes">(' + _('Allowed mime types: ') + str(ls.ELFINDER_CONNECTOR_OPTION_SETS[self.optionset]['uploadAllow']) + ')</div>'

        #update the elfinder client options
        self.options.update({ 
            'url' : reverse('yawdElfinderConnectorView', args=[
                    self.optionset, 
                    'default' if self.start_path is None else self.start_path
                ]),
            'rememberLastDir' : True if not self.start_path else False,
        })
        
        if not 'rmSoundUrl' in self.options:
            self.options['rmSoundUrl'] = '%selfinder/sounds/rm.wav' % settings.STATIC_URL
        
        #update the elfinder client language
        if not self.current_locale.startswith('en') and self.current_locale in ls.ELFINDER_LANGUAGES:
            self.options.update({ 'lang' : self.current_locale })

        if value:
            if not isinstance(value, ElfinderFile):
                value = ElfinderFile(hash_=value, optionset=self.optionset)
            file_ = 'file : %s' % json.dumps(value.info)
        else:
            file_ = 'file : {}'
        
        elfinder = 'elfinder : %s' % json.dumps(self.options) 
        #'            $("#%(id)s").attr("disabled","disabled");\n' 
        html = ('%(super)s\n'
                '<script>\n'
                '    (function($) {\n'
                '        $(document).ready( function() {\n'
                '            $("#%(id)s").elfinderwidget({\n'
                '                %(file)s,\n'
                '                %(elfinder)s,\n'
                '                keywords : { size : "%(size)s", path : "%(path)s", link : "%(link)s", modified : "%(modified)s", dimensions : "%(dimensions)s", update : "%(update)s", set : "%(set)s", clear : "%(clear)s" }'
                '            });\n'
                '        })\n'
                '    })(yawdelfinder.jQuery)\n'
                '</script>' % {
                    'super' : super(ElfinderWidget, self).render(name, value, attrs),
                    'id' : attrs['id'],
                    'file' : file_,
                    'elfinder' : elfinder,
                    #these keywords are optional, since they are initialized in elfinderwidget
                    #we override them for localization purposes
                    'size' : _('Size'),
                    'path' : _('Path'),
                    'link' : _('Link'),
                    'modified' : _('Modified'),
                    'dimensions' : _('Dimensions'),
                    'update' : _('Update'),
                    'set' : _('Set'),
                    'clear' : _('Clear')
                })
        #print super(ElfinderWidget, self).render(name, value, attrs)
        #print html
        return mark_safe(html)
