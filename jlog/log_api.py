# coding: utf-8


from argparse import ArgumentParser, FileType
from contextlib import closing
from codecs import open as copen
from json import dumps
from math import ceil
from os.path import basename, dirname, exists, join
from struct import unpack
from subprocess import Popen
from sys import platform, prefix, stderr
from tempfile import NamedTemporaryFile

from jinja2 import FileSystemLoader, Template
from jinja2.environment import Environment

from jumpserver.api import BASE_DIR


DEFAULT_TEMPLATE = join(BASE_DIR, 'templates', 'jlog', 'static.jinja2')


def escapeString(string):
    string = string.encode('unicode_escape').decode('utf-8')
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
        scriptf.readline()  # ignore first header line from script file
        offset = 0
        for t in timing:
            dt = scriptf.read(t[1])
            print "## %s: %s" % (t, dt)
            data = escapeString(dt)
            offset += t[0]
            ret.append((data, offset))
        print ret
    return dumps(ret)


def renderTemplate(script_path, time_file_path, dimensions=(24, 80), templatename=DEFAULT_TEMPLATE):
    #with copen(script_path, encoding='utf-8', errors='replace') as scriptf:
    with open(script_path) as scriptf:
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


