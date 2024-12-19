import curses
from curses import window
from .utils import *
from .consts import *
from threading import Event

class _CurseWidget:
    def __init__(self):
        self._self: window = ...

    def __getattr__(self, name):
        return getattr(self._self, name)

class Console(_CurseWidget):
    def __init__(self, parent: window):
        self.parent = parent
        x, y = parent.getmaxyx()
        self._self: window = curses.newpad(x*2, y*2)

    def refresh(self):
        lay(self._self, self.parent)

    def out(self, text: str):
        '''puts text onto console pad and lays pad onto game area'''
        self._self.addstr(text)
        lay(self._self, self.parent)
        curses.doupdate()

    def cls(self):
        '''clears console pad'''
        self._self.clear()
        cover(self.parent)
        curses.doupdate()

class TextBox(_CurseWidget):
    def __init__(self, nline, ncols, beg_y, beg_x):
        self.outline = curses.newwin(nline, ncols, beg_y, beg_x)
        self.outline.box()
        self._self = curses.newwin(nline - 2, ncols - 2, beg_y + 1, beg_x + 1)

        self.outline.noutrefresh()

        self.message = ""
        self.message_buffer = []
        self.submission = Event()

    def proc_key(self, key: str):
        if key == ENTER:
            self.submission.set()
            self.message = "".join(self.message_buffer)
            self.clear_text()
        elif key == BKSP and len(self.message_buffer) > 0:
            self._self.delch(0, len(self.message_buffer) - 1)
            self.message_buffer.pop()
        elif key == CTRL_BKSP:
            buffer_length = len(self.message_buffer)
            index = 0 if not ' ' in self.message_buffer else\
                    buffer_length - self.message_buffer[::-1].index(' ') - 1
            word_len = buffer_length - index
            self._self.move(0, index)
            self._self.addstr(word_len * ' ') # covers the existing word
            self._self.move(0, index)
            self.message_buffer = self.message_buffer[:index]
        elif is_printable(key) and len(self.message_buffer) < self._self.getmaxyx()[1] - 1:
                self._self.addch(key)
                self.message_buffer.append(key)
        self._self.refresh()
    
    def clear_text(self):
        self.message_buffer = []
        self._self.deleteln()
        self._self.move(0, 0)

    def get_text(self):
        self.submission.clear() 
        self.submission.wait()
        self.submission.clear()
        return self.message

class Panel(_CurseWidget):
    def __init__(self, nline: int, ncols: int, beg_y: int, beg_x: int, outline = False):
        if outline:
            self.border = curses.newwin(nline, ncols, beg_y, beg_x)
            self.border.box()
            self.border.noutrefresh()
            self._self = curses.newwin(nline - 2, ncols - 2, beg_y + 1, beg_x + 1)
        else:
            self._self = curses.newwin(nline, ncols, beg_y, beg_x)
    
    def show(self):
        cover(self._self)

    def hide(self):
        uncover(self._self)