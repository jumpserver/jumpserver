# coding: utf-8

import time
import json
import os.path

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import tornado.httpserver

from tornado.options import define, options

define("port", default=8080, help="run on the given port", type=int)


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

    def open(self):
        SendHandler.clients.add(self)
        self.write_message(json.dumps({'input': 'connected...'}))
        self.stream.set_nodelay(True)

    def on_message(self, message):
        message = json.loads(message)
        self.write_message(json.dumps({'input': 'response...'}))
        while True:
            self.write_message(json.dumps(message))
            time.sleep(1)
        # # 服务器主动关闭
        # self.close()
        # SendHandler.clients.remove(self)

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
