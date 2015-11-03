# coding: utf-8

import time
import json
import os
import sys
import os.path

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.gen

from tornado.options import define, options
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_DELETE, IN_CREATE, IN_MODIFY

define("port", default=8080, help="run on the given port", type=int)
define("host", default='0.0.0.0', help="run port on", type=str)


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
    notifier = Notifier(wm, EventHandler(client))
    wm.add_watch(path, mask, auto_add=True, rec=True)
    if not os.path.isfile(path):
        print "You should monitor a file"
        sys.exit(3)
    else:
        print "now starting monitor %s." %path
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
            (r'/', MainHandler),
            (r'/monitor', MonitorHandler),
        ]

        setting = {
            'cookie_secret': 'DFksdfsasdfkasdfFKwlwfsdfsa1204mx',
            'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
            'static_path': os.path.join(os.path.dirname(__file__), 'static'),
        }

        tornado.web.Application.__init__(self, handlers, **setting)


class MonitorHandler(tornado.websocket.WebSocketHandler):
    clients = set()

    def __init__(self, *args, **kwargs):
        self.file_path = None
        super(self.__class__, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    def open(self):
        # 获取监控的path
        self.file_path = self.get_argument('file_path', '')
        MonitorHandler.clients.add(self)
        self.stream.set_nodelay(True)

    def on_message(self, message):
        self.write_message('Connect WebSocket Success. <br/>')
        # 监控日志，发生变动发向客户端
        file_monitor('%s.log' % self.file_path, client=self)
        self.write_message('Disconnect WebSocket.<br/>')

    def on_close(self):
        # 客户端主动关闭
        self.close()
        self.finish()
        MonitorHandler.clients.remove(self)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('log_watch.html')


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.bind(options.port, options.host)
    # server.listen(options.port)
    server.start(num_processes=1)
    tornado.ioloop.IOLoop.instance().start()
