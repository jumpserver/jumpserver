class PiicoError(Exception):
    def __init__(self, msg, ret):
        super().__init__(self)
        self.__ret = ret
        self.__msg = msg

    def __str__(self):
        return "piico error: {} return code: {}".format(self.__msg, self.hex_ret(self.__ret))

    @staticmethod
    def hex_ret(ret):
        return hex(ret & ((1 << 32) - 1))
