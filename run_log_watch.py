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

from tornado.options import define, options
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_DELETE, IN_CREATE, IN_MODIFY

define("port", default=8080, help="run on the given port", type=int)


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
            (r'/send', SendHandler),
        ]

        setting = {
            'cookie_secret': 'DFksdfsasdfkasdfFKwlwfsdfsa1204mx',
            'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
            'static_path': os.path.join(os.path.dirname(__file__), 'static'),
        }

        tornado.web.Application.__init__(self, handlers, **setting)


class SendHandler(tornado.websocket.WebSocketHandler):
    clients = set()

    def check_origin(self, origin):
        return True

    def open(self):
        SendHandler.clients.add(self)
        self.stream.set_nodelay(True)

    def on_message(self, message):
        self.write_message(message)
        # while True:
        #     self.write_message(json.dumps(message))
        #     time.sleep(1)
        # # 服务器主动关闭
        # self.close()
        # SendHandler.clients.remove(self)

        file_monitor('/opt/jumpserver/logs/tty/20151102/a_b_191034.log', client=self)
        self.write_message('monitor /tmp/test1234')

    def on_close(self):
        # 客户端主动关闭
        SendHandler.clients.remove(self)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('log_watch.html')


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
