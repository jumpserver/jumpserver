# coding: utf-8

import time
import datetime
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
from connect import Tty
from connect import TtyLog

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

        print len(MonitorHandler.threads), len(MonitorHandler.clients)

    def on_message(self, message):
        # 监控日志，发生变动发向客户端
        pass

    def on_close(self):
        # 客户端主动关闭
        # self.close()

        print "Close websocket."
        client_index = MonitorHandler.clients.index(self)
        MonitorHandler.clients.remove(self)
        MonitorHandler.threads.remove(MonitorHandler.threads[client_index])


class WebTty(Tty):
    def __init__(self, *args, **kwargs):
        super(WebTty, self).__init__(*args, **kwargs)
        self.login_type = 'web'
        self.ws = None
        self.input_r = ''
        self.input_mode = False


class WebTerminalHandler(tornado.websocket.WebSocketHandler):
    tasks = []

    def __init__(self, *args, **kwargs):
        self.term = None
        self.channel = None
        self.log_file_f = None
        self.log_time_f = None
        self.log = None
        super(WebTerminalHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    def open(self):
        self.term = WebTty('a', 'b')
        self.term.get_connection()
        self.channel = self.term.ssh.invoke_shell(term='xterm')
        WebTerminalHandler.tasks.append(MyThread(target=self.forward_outbound))

        for t in WebTerminalHandler.tasks:
            if t.is_alive():
                continue
            t.setDaemon(True)
            t.start()

    def on_message(self, message):
        data = json.loads(message)
        if not data:
            return
        if data.get('data'):
            self.term.input_mode = True
            if str(data['data']) in ['\r', '\n', '\r\n']:
                TtyLog(log=self.log, datetime=datetime.datetime.now(), cmd=self.term.remove_control_char(self.term.input_r)).save()
                self.term.input_r = ''
                self.term.input_mode = False
            self.channel.send(data['data'])

    def on_close(self):
        print 'On_close'
        self.log_file_f.write('End time is %s' % datetime.datetime.now())
        self.log.is_finished = True
        self.log.end_time = datetime.datetime.now()
        self.log.save()
        self.close()

    def forward_outbound(self):
        self.log_file_f, self.log_time_f, self.log = self.term.get_log_file()
        try:
            data = ''
            pre_timestamp = time.time()
            while True:
                r, w, e = select.select([self.channel, sys.stdin], [], [])
                if self.channel in r:
                    recv = self.channel.recv(1024)
                    if not len(recv):
                        return
                    data += recv
                    try:
                        self.write_message(json.dumps({'data': data}))
                        now_timestamp = time.time()
                        self.log_time_f.write('%s %s\n' % (round(now_timestamp-pre_timestamp, 4), len(data)))
                        self.log_file_f.write(data)
                        pre_timestamp = now_timestamp
                        self.log_file_f.flush()
                        self.log_time_f.flush()
                        if self.term.input_mode and not self.term.is_output(data):
                            self.term.input_r += data
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
