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
    def __init__(self, parent: window, multiplier = 2):
        self.parent = parent
        self.reset_offset()
        height, width = parent.getmaxyx()
        self._self: window = curses.newpad(height*multiplier, width*multiplier)

    def refresh(self):
        '''Make any update to the Console on the parent visible if not already.'''
        lay(self._self, self.parent, self.cur_y, self.cur_x)
        curses.doupdate()
    
    def shift(self, dir: Dir, unit: int = 1):
        '''Shift the console in "dir" directiion "unit" units.'''
        match (dir):
            case Dir.UP:
                max_y = self._self.getmaxyx()[0] - 1
                self.cur_y += unit if self.cur_y + unit <= max_y else 0
            case Dir.DOWN: 
                self.cur_y -= unit if self.cur_y - unit >= 0 else 0
            case Dir.LEFT:
                max_x = self._self.getmaxyx()[1] - 1
                self.cur_x += unit if self.cur_x + unit <= max_x else 0
            case Dir.RIGHT:
                self.cur_x -= unit if self.cur_x - unit >= 0 else 0
    
    def reset_offset(self):
        '''Bring Console back to starting location on parent'''
        self.cur_y, self.cur_x = 0, 0

    def get_offset(self):
        return self.cur_y, self.cur_x

    def out(self, text: str):
        '''Addstr to Console and updates the screen'''
        self._self.addstr(text)
        self.refresh()

    def cls(self):
        '''Clear the Console and update the screen'''
        self._self.clear()
        cover(self.parent)

class TextBox(_CurseWidget):
    def __init__(self, nline, ncols, beg_y, beg_x):
        self.border = curses.newwin(nline, ncols, beg_y, beg_x)
        self._self = curses.newwin(nline - 2, ncols - 2, beg_y + 1, beg_x + 1)
        self.message = ""
        self.message_buffer = []
        self.submission = Event()
    
    def noutrefresh(self):
        self.border.box()
        reprint_win(self._self)
        self.border.noutrefresh()
        self._self.noutrefresh()

    def refresh(self):
        self.noutrefresh()
        curses.doupdate()

    def proc_key(self, key: ChType):
        '''
        Process a keystroke.\n
        Supports Enter, Backspace, Ctrl-Backspace, and Printable Chars.\n
        Use cursestools.consts for most reliable results.'''
        if key == ENTER:
            self.submission.set()
            self.message = self.peek_text()
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
        self.refresh()
    
    def clear_text(self):
        '''Clears the message buffer'''
        self.message_buffer = []
        self._self.deleteln()
        self._self.move(0, 0)

    def get_text(self):
        '''Waits for submission event then returns whats stored in the message field'''
        self.submission.clear() 
        self.submission.wait()
        self.submission.clear()
        return self.message

    def peek_text(self):
        '''Return text currently stored in textbox'''
        return "".join(self.message_buffer)

class Panel(_CurseWidget):
    def __init__(self, nline: int, ncols: int, beg_y: int, beg_x: int, outline = False):
        self.outline = outline
        if outline:
            self.border = curses.newwin(nline, ncols, beg_y, beg_x)
            self._self = curses.newwin(nline - 2, ncols - 2, beg_y + 1, beg_x + 1)
        else:
            self._self = curses.newwin(nline, ncols, beg_y, beg_x)
        self.visible = True
        self.overlay = None

    def noutrefresh(self):
        if self.outline:
            self.border.box()
            reprint_win(self._self)
            self.border.noutrefresh()
        self._self.noutrefresh()

    def refresh(self):
        self.noutrefresh()
        curses.doupdate()
    
    def set_overlay(self, overlay: Pad):
        '''
        Set an overlay to be shown and hidden with the panel.\n
        Setting an overlay does not destroy what is stored in the panel.'''
        self.overlay = overlay
    
    def remove_overlay(self):
        '''Removes overlay, and therefore, will not show overlay on .show()'''
        self.overlay = None
    
    def toggle(self):
        '''toggle Panel visibility'''
        self.hide() if self.visible else self.show()
    
    def show(self):
        '''Display any content in panel, or overlay if present'''
        self.visible = True
        if self.outline:
            self.border.box()
            self.border.noutrefresh()
        uncover(self._self)
        if self.overlay:
            lay(self.overlay, self._self)
        
    def hide(self):
        '''
        Hide any content in panel, or overlay if present\n
        Content in Panel and overlay are preserved'''
        self.visible = False
        self.noutrefresh()
        cover(self._self)
        