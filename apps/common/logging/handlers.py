from logging.handlers import SysLogHandler, SYSLOG_UDP_PORT
import socket


class TcpSyslogHandler(SysLogHandler):
    """
    This class override the python SyslogHandler emit function.
    It is needed to deal with appending of the nul character to the end of the message when using TCP.
    Please see: https://stackoverflow.com/questions/40041697/pythons-sysloghandler-and-tcp/40152493#40152493
    """

    def __init__(self, message_separator_char, address=('localhost', SYSLOG_UDP_PORT),
                 facility=SysLogHandler.LOG_USER, socktype=None):
        """
        The user of this class must specify the value for the messages separator.
        :param message_separator_char: The value to separate between messages.
                                            The recommended value is the "nul character": "\000".
        :param address: Same as in the super class.
        :param facility: Same as in the super class.
        :param socktype: Same as in the super class.
        """
        super(TcpSyslogHandler, self).__init__(address=address, facility=facility, socktype=socktype)

        self.message_separator_char = message_separator_char

    def emit(self, record):
        """
        SFTCP addition:
        To let the user to choose which message_separator_char to use, we override the emit function.
        ####
        Emit a record.

        The record is formatted, and then sent to the syslog server. If
        exception information is present, it is NOT sent to the server.
        """
        try:
            msg = self.format(record) + self.message_separator_char
            if self.ident:
                msg = self.ident + msg

            # We need to convert record level to lowercase, maybe this will
            # change in the future.
            prio = '<%d>' % self.encodePriority(self.facility,
                                                self.mapPriority(record.levelname))
            prio = prio.encode('utf-8')
            # Message is a string. Convert to bytes as required by RFC 5424
            msg = msg.encode('utf-8')
            msg = prio + msg
            if self.unixsocket:
                try:
                    self.socket.send(msg)
                except OSError:
                    self.socket.close()
                    self._connect_unixsocket(self.address)
                    self.socket.send(msg)
            elif self.socktype == socket.SOCK_DGRAM:
                self.socket.sendto(msg, self.address)
            else:
                self.socket.sendall(msg)
        except Exception:
            self.handleError(record)
