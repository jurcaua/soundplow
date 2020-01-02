from singleton import Singleton
from enum import Enum

from PySide2.QtGui import QTextCharFormat, QBrush, QColor

MessageType = Enum('MessageType', 'INFO WARNING ERROR SUCCESS')

class UndefinedMessageType(RuntimeError):
    pass

@Singleton
class Log(object):
    def __init__(self):
        pass

    def load(self, textbox):
        self.textbox = textbox
        self.text_cursor = self.textbox.textCursor()

    def log(self, text, level=MessageType.INFO):
        if level is MessageType.INFO:
            color = "000000"
        elif level is MessageType.WARNING:
            color = "#9ece2f"
        elif level is MessageType.ERROR:
            color = "#ed2d2d"
        elif level is MessageType.SUCCESS:
            color = "#4dd30a"
        else:
            raise UndefinedMessageType("Undefined message type: {type}.".format(type=level))

        line_format = QTextCharFormat()
        line_format.setForeground(QBrush(QColor(color)))
        self.text_cursor.setCharFormat(line_format)

        self.text_cursor.insertText(text + "\n")
        self.textbox.verticalScrollBar().setValue(self.textbox.verticalScrollBar().maximum())

    def info(self, text):
        self.log(text, MessageType.INFO)

    def warning(self, text):
        self.log(text, MessageType.WARNING)

    def error(self, text):
        self.log(text, MessageType.ERROR)

    def success(self, text):
        self.log(text, MessageType.SUCCESS)
