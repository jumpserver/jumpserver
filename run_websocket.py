# coding: utf-8

import time
import json
import os
import sys
import os.path
import threading

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.gen
from tornado.websocket import WebSocketClosedError

from tornado.options import define, options
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_DELETE, IN_CREATE, IN_MODIFY, AsyncNotifier

# from gevent import monkey
# monkey.patch_all()
# import gevent
# from gevent.socket import wait_read, wait_write
import struct, fcntl, signal, socket, select, fnmatch

import paramiko

try:
    import simplejson as json
except ImportError:
    import json


define("port", default=3000, help="run on the given port", type=int)
define("host", default='0.0.0.0', help="run port on", type=str)


class MyThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(MyThread, self).__init__(*args, **kwargs)

    def run(self):
        try:
            super(MyThread, self).run()
        except WebSocketClosedError:
            pass


class EventHandler(ProcessEvent):
    def __init__(self, client=None):
        self.client = client

    def process_IN_CREATE(self, event):
        print "Create file:%s." % os.path.join(event.path, event.name)

    def process_IN_DELETE(self, event):
        print "Delete file:%s." % os.path.join(event.path, event.name)

    def process_IN_MODIFY(self, event):
        print "Modify file:%s." % os.path.join(event.path, event.name)
        self.client.write_message(f.read())


def file_monitor(path='.', client=None):
    wm = WatchManager()
    mask = IN_DELETE | IN_CREATE | IN_MODIFY
    notifier = AsyncNotifier(wm, EventHandler(client))
    wm.add_watch(path, mask, auto_add=True, rec=True)
    if not os.path.isfile(path):
        print "You should monitor a file"
        sys.exit(3)
    else:
        print "now starting monitor %s." % path
        global f
        f = open(path, 'r')
        st_size = os.stat(path)[6]
        f.seek(st_size)

    while True:
        try:
            notifier.process_events()
            if notifier.check_events():
                notifier.read_events()
        except KeyboardInterrupt:
            print "keyboard Interrupt."
            notifier.stop()
            break


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/monitor', MonitorHandler),
            (r'/terminal', WebTerminalHandler),
        ]

        setting = {
            'cookie_secret': 'DFksdfsasdfkasdfFKwlwfsdfsa1204mx',
            'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
            'static_path': os.path.join(os.path.dirname(__file__), 'static'),
            'debug': True,
        }

        tornado.web.Application.__init__(self, handlers, **setting)


class MonitorHandler(tornado.websocket.WebSocketHandler):
    clients = []
    threads = []

    def __init__(self, *args, **kwargs):
        self.file_path = None
        super(self.__class__, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    def open(self):
        # 获取监控的path
        self.file_path = self.get_argument('file_path', '')
        MonitorHandler.clients.append(self)
        thread = MyThread(target=file_monitor, args=('%s.log' % self.file_path, self))
        MonitorHandler.threads.append(thread)
        self.stream.set_nodelay(True)

        print len(MonitorHandler.threads), len(MonitorHandler.clients)

    def on_message(self, message):
        self.write_message('Connect WebSocket Success. <br/>')
        # 监控日志，发生变动发向客户端

        try:
            for t in MonitorHandler.threads:
                if t.is_alive():
                    continue
                t.setDaemon(True)
                t.start()

        except WebSocketClosedError:
            client_index = MonitorHandler.clients.index(self)
            MonitorHandler.threads[client_index].stop()
            MonitorHandler.clients.remove(self)
            MonitorHandler.threads.remove(MonitorHandler.threads[client_index])

    def on_close(self):
        # 客户端主动关闭
        # self.close()

        print "Close websocket."
        client_index = MonitorHandler.clients.index(self)
        MonitorHandler.clients.remove(self)
        MonitorHandler.threads.remove(MonitorHandler.threads[client_index])


class WebTerminalHandler(tornado.websocket.WebSocketHandler):
    tasks = []

    def __init__(self, *args, **kwargs):
        self.chan = None
        self.ssh = None
        super(WebTerminalHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    def open(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect('127.0.0.1', 22, 'root', 'redhat')
        except:
            self.write_message(json.loads({'data': 'Connect server Error'}))
            self.close()

        self.chan = self.ssh.invoke_shell(term='xterm')
        WebTerminalHandler.tasks.append(threading.Thread(target=self._forward_outbound))

        for t in WebTerminalHandler.tasks:
            if t.is_alive():
                continue
            t.setDaemon(True)
            t.start()

    def on_message(self, message):
        data = json.loads(message)
        if not data:
            return
        if 'resize' in data:
            self.chan.resize_pty(
                data['resize'].get('width', 80),
                data['resize'].get('height', 24))
        if 'data' in data:
            self.chan.send(data['data'])

    def on_close(self):
        self.write_message(json.dumps({'data': 'close websocket'}))

    def _forward_outbound(self):
        """ Forward outbound traffic (ssh -> websockets) """
        try:
            data = ''
            while True:
                r, w, e = select.select([self.chan, sys.stdin], [], [])
                if self.chan in r:
                    recv = self.chan.recv(1024)
                    print recv
                    if not len(recv):
                        return
                    data += recv
                    try:
                        self.write_message(json.dumps({'data': data}))
                        data = ''
                    except UnicodeDecodeError:
                        pass
        finally:
            self.close()


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.bind(options.port, options.host)
    # server.listen(options.port)
    server.start(num_processes=1)
    tornado.ioloop.IOLoop.instance().start()
