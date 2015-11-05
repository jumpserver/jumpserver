#!/usr/bin/env python
__author__ = 'liuzheng'

import sys
import os
import re
from tornado.options import options, define, parse_command_line
import tornado.wsgi
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.ioloop
import tornado.websocket
import pty
import io
import struct
import string
import random
import fcntl
import termios
import tornado.process
import tornado.options
import signal
import utils
import getpass
from connect import Jtty

define('port', type=int, default=8000)

ioloop = tornado.ioloop.IOLoop.instance()

class Terminal(tornado.websocket.WebSocketHandler):
    terminals = set()

    def pty(self):
        # Make a "unique" id in 4 bytes
        self.uid = ''.join(
            random.choice(
                string.ascii_lowercase + string.ascii_uppercase +
                string.digits)
            for _ in range(4))

        self.pid, self.fd = pty.fork()
        # print "pid:",self.pid,"fd",self.fd,"uid",self.uid
        if self.pid == 0:
            # print "Login as", self.user
            os.execv("/usr/bin/ssh", [self.user, "localhost"])
            # self.callee = utils.User(name=self.user)
            # self.determine_user()
            self.shell()
        else:
            self.communicate()

    def determine_user(self):
        if self.callee is None:
            # If callee is now known and we have unsecure connection
            user = self.user

            try:
                self.callee = utils.User(name=user)
            except Exception:
                # self.log.debug("Can't switch to user %s" % user, exc_info=True)
                self.callee = utils.User(name='nobody')

        assert self.callee is not None

    def shell(self):
        try:
            os.chdir(self.path or self.callee.dir)
        except Exception:
            pass
        env = os.environ
        # If local and local user is the same as login user
        # We set the env of the user from the browser
        # Usefull when running as root
        if self.caller == self.callee:
            env.update(self.socket.env)
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "butterfly"
        env["HOME"] = self.callee.dir
        # print(self.callee.dir)
        env["LOCATION"] = "http%s://%s:%d/" % (
            "s" if not True else "",
            "localhost", 8001)
        env["PATH"] = '%s:%s' % (os.path.abspath(os.path.join(
            os.path.dirname(__file__), 'bin')), env.get("PATH"))

        try:
            tty = os.ttyname(0).replace('/dev/', '')
        except Exception:
            tty = ''

        if self.caller != self.callee:
            try:
                os.chown(os.ttyname(0), self.callee.uid, -1)
            except Exception:
                pass

        utils.add_user_info(
            self.uid,
            tty, os.getpid(),
            self.callee.name, self.request.headers['Host'])

        if os.path.exists('/usr/bin/su'):
            args = ['/usr/bin/su']
        else:
            args = ['/bin/su']

        if sys.platform == 'linux':
            args.append('-p')
            if tornado.options.options.shell:
                args.append('-s')
                args.append(tornado.options.options.shell)
        args.append(self.callee.name)
        os.execvpe(args[0], args, env)

    def communicate(self):
        fcntl.fcntl(self.fd, fcntl.F_SETFL, os.O_NONBLOCK)

        self.reader = io.open(
            self.fd,
            'rb',
            buffering=0,
            closefd=False
        )
        self.writer = io.open(
            self.fd,
            'wt',
            encoding='utf-8',
            closefd=False
        )
        ioloop.add_handler(
            self.fd, self.shellHandle, ioloop.READ | ioloop.ERROR)

    def allow_draft76(self):
        # for iOS 5.0 Safari
        return True

    def check_origin(self, origin):
        return True

    def open(self):
        print "term socket open"
        self.fd = None
        self.closed = False
        self.socket = utils.Socket(self.ws_connection.stream.socket)
        self.set_nodelay(True)
        self.path = None
        self.user = getpass.getuser()
        self.caller = self.callee = None
        # self.user = "liuzheng"
        self.callee = None

        Terminal.terminals.add(self)

        self.pty()
        print self.fd

    def on_message(self, msg):
        print "on_message ", msg
        if not hasattr(self, 'writer'):
            self.on_close()
            self.close()
            return
        if msg[0] == 'C':  # Change screen
            c, r = map(int, msg[1:].split(','))
            s = struct.pack("HHHH", r, c, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, s)
        elif msg[0] == 'R':  # Run shell
            self.writer.write(msg[1:])
            self.writer.flush()

    def shellHandle(self, f, events):
        if events & ioloop.READ:
            try:
                read = self.reader.read()
            except IOError:
                read = ''

            if read and len(read) != 0 and self.ws_connection:
                self.write_message(read.decode('utf-8', 'replace'))
            else:
                events = ioloop.ERROR

        if events & ioloop.ERROR:
            self.on_close()
            self.close()

    def on_close(self):
        print "term close", self.uid
        if self.closed:
            return
        self.closed = True

        if getattr(self, 'pid', 0) == 0:
            return

        utils.rm_user_info(self.uid, self.pid)

        try:
            ioloop.remove_handler(self.fd)
        except Exception:
            pass

        try:
            os.close(self.fd)
        except Exception:
            pass
        try:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
        except Exception:
            pass
        Terminal.terminals.remove(self)


class Index(tornado.web.RequestHandler):
    def get(self):
        self.render('templates/terminal.html')


def main():
    sys.path.append('./jumpserver')  # path to your project if needed

    parse_command_line()

    tornado_app = tornado.web.Application(
        [
            ('/ws/terminal', Terminal),
            ('/ws/Terminal', Index),
        ])

    server = tornado.httpserver.HTTPServer(tornado_app)
    server.listen(options.port)

    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
