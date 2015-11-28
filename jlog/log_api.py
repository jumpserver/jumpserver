# coding: utf-8


from argparse import ArgumentParser, FileType
from contextlib import closing
from io import open as copen
from json import dumps
from math import ceil
import re
from os.path import basename, dirname, exists, join
from struct import unpack
from subprocess import Popen
from sys import platform, prefix, stderr
from tempfile import NamedTemporaryFile

from jinja2 import FileSystemLoader, Template
from jinja2.environment import Environment

from jumpserver.api import BASE_DIR


DEFAULT_TEMPLATE = join(BASE_DIR, 'templates', 'jlog', 'static.jinja2')
rz_pat = re.compile(r'\x18B\w+\r\x8a(\x11)?')


def escapeString(string):
    string = rz_pat.sub('', string)
    try:
        string = string.encode('unicode_escape').decode('utf-8', 'ignore')
    except (UnicodeEncodeError, UnicodeDecodeError):
        string = string.decode('utf-8', 'ignore')
    string = string.replace("'", "\\'")
    string = '\'' + string + '\''
    return string


def getTiming(timef):
    timing = None
    with closing(timef):
        timing = [l.strip().split(' ') for l in timef]
        timing = [(int(ceil(float(r[0]) * 1000)), int(r[1])) for r in timing]
    return timing


def scriptToJSON(scriptf, timing=None):
    ret = []

    with closing(scriptf):
        print "# %s #" % scriptf.readline()  # ignore first header line from script file
        offset = 0
        for t in timing:
            dt = scriptf.read(t[1])
            data = escapeString(dt)
            print ('###### (%s, %s)' % (t[1], repr(data)))
            offset += t[0]
            ret.append((data, offset))
    return dumps(ret)


def renderTemplate(script_path, time_file_path, dimensions=(24, 80), templatename=DEFAULT_TEMPLATE):
    with copen(script_path, encoding='utf-8', errors='replace', newline='\r\n') as scriptf:
    # with open(script_path) as scriptf:
        with open(time_file_path) as timef:
            timing = getTiming(timef)
            json = scriptToJSON(scriptf, timing)

    fsl = FileSystemLoader(dirname(templatename), 'utf-8')
    e = Environment()
    e.loader = fsl

    templatename = basename(templatename)
    rendered = e.get_template(templatename).render(json=json,
                                                   dimensions=dimensions)

    return rendered


