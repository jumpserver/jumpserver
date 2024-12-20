from termcolor import COLORS


class ColoredPrinter(object):
    _red = 'light_red'
    _green = 'light_green'
    _yellow = 'light_yellow'
    _grey = 'light_grey'
    _white = 'white'

    @staticmethod
    def polish(text, color):
        fmt = u"\033[%sm%s\033[0m"
        color_code = u'0;%s' % COLORS[color]
        return u"\n".join([fmt % (color_code, t) for t in text.split(u'\n')])

    @staticmethod
    def _print(text):
        print(text)

    def red(self, text):
        self._print(self.polish(text=text, color=self._red))

    def green(self, text):
        self._print(self.polish(text=text, color=self._green))

    def yellow(self, text):
        self._print(self.polish(text=text, color=self._yellow))

    def info(self, text):
        self._print(self.polish(text=text, color=self._grey))

    def line(self, output='=', length=60):
        text = '{}{}'.format('\n', output * length)
        self._print(self.polish(text=text, color=self._white))


class ColoredFilePrinter(ColoredPrinter):
    def __init__(self, file, flush_now=False):
        self.file = file
        self.flush_now = flush_now

    def _print(self, text):
        self.file.write(text + '\r\n')
        if self.flush_now:
            self.file.flush()

    def close(self):
        try:
            self.file.close()
        except: # noqa
            pass

    def __del__(self):
        self.close()
