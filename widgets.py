import curses
from curses import window
from .utils import *
from .consts import *
from threading import Event
from typing import Literal

class _CurseWidget:
    def __init__(self):
        self._self: window = ...

    def __getattr__(self, name):
        return getattr(self._self, name)

class Page(_CurseWidget):
    def __init__(self, parent: window, *, multiplier = 1, height = 0, width = 0):
        self.parent = parent
        self.reset_offset()
        temph, tempw = parent.getmaxyx()
        if not height:
            height = temph
        if not width:
            width = tempw
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

    def out(self, text: str, end = '\n'):
        '''print to Console and update the screen'''
        self._self.addstr(text + end)
        self.refresh()

    def cls(self):
        '''Clear the Console and update the screen'''
        self._self.clear()
        cover(self.parent)
        
class Terminal(_CurseWidget):
    def __init__(self, nline, ncols, beg_y, beg_x):
        self.border = curses.newwin(nline, ncols, beg_y, beg_x)
        self._self = self.border.subwin(nline - 2, ncols - 2, beg_y + 1, beg_x + 1)
        self.message = ""
        self.message_buffer = []
        self.submission = Event()
    
    def noutrefresh(self):
        self.border.box()
        self.border.noutrefresh()

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
        elif key.isprintable() and len(self.message_buffer) < self._self.getmaxyx()[1] - 1:
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

class TextBox:
    def __init__(self, nlines: int, ncols: int, beg_y: int, beg_x: int,\
                        text: str = "", align = Align.LEFT):
        self.nlines = nlines
        self.ncols = ncols
        self.width = ncols - 2
        self.frame = curses.newwin(nlines, ncols, beg_y, beg_x)
        self._self = self.frame.derwin(nlines, ncols - 2, 0, 1)
        self.align = align
        self.text = text

    def set_text(self, text: str):
        self.text = text

    def set_align(self, align: Align):
        self.align = align

    def noutprint(self):
        self.clear()
        self.format()
        self.frame.vline(0, 0, curses.ACS_VLINE, self.nlines)
        self.frame.vline(0, self.ncols - 1, curses.ACS_VLINE, self.nlines)
        self.frame.noutrefresh()
        self._self.noutrefresh()
    
    def print(self):
        self.noutprint()
        curses.doupdate()

    def clear(self):
        self.frame.clear()

    def read(self, mode: Literal["WORD"] | Literal["CHAR"] = "CHAR", timeout: float = 0.05):
        if mode == "WORD":
            builder = []
            itera = self.text.split()
        elif mode == "CHAR":
            builder = ""
            itera = self.text
        else:
            raise Exception("Invalid Mode")
        
        for block in itera:
            if mode == "WORD":
                builder.append(block)
                text = " ".join(builder)
                self.set_text(text)
            if mode == "CHAR":
                builder += block
                self.set_text(builder)
            self.print()
            sleep(timeout)

    def format(self):
        current_line_length = 0
        current_line = []
        y = 0
        for word in self.text.split():
            line = []
            word_length = len(word)
            if current_line_length + 1 + word_length > self.width:
                line = " ".join(current_line)
                self.put(y, line)
                current_line = [word]
                current_line_length = word_length
                y += 1
            else:
                current_line.append(word)
                current_line_length += 1 + word_length
        if current_line:
            line = " ".join(current_line)
            self.put(y, line)
    
    def put(self, y, line):
        # writing in bottom left corner will automatically wrap to next line
        # which may be out of bounds causing exception.
        # we will just except it here and pass
        if y > self.nlines:
            raise curses.error
        try:
            self._self.addstr(y, self.get_offset(line, self.align), line)
        except curses.error:
            pass 

    
    def get_offset(self, line: str, alignment: Align):
        length_line = len(line)
        match (alignment):
            case Align.RIGHT:
                return (self.width - length_line)
            case Align.CENTER:
                return (self.width - length_line) // 2
            case Align.LEFT:
                ...
        return 0
        
class Panel(_CurseWidget):
    def __init__(self, nline: int, ncols: int, beg_y: int, beg_x: int, outline: bool = False):
        self.outline = outline
        if self.outline:
            self.border = curses.newwin(nline, ncols, beg_y, beg_x)
            self._self = self.border.subwin(nline - 2, ncols - 2, beg_y + 1, beg_x + 1)
        else:
            self._self = curses.newwin(nline, ncols, beg_y, beg_x)
        self.visible = True
    
    def refresh_border(self):
        self.border.box()
        self.border.noutrefresh()

    def noutrefresh(self):
        if self.outline:
            self.refresh_border()
        else:
            self._self.noutrefresh()

    def refresh(self):
        self.noutrefresh()
        curses.doupdate()
    
    def toggle(self):
        '''toggle Panel visibility'''
        self.hide() if self.visible else self.show()
    
    def show(self):
        '''Display any content in panel, or overlay if present'''
        self.visible = True
        if self.outline:
            self.refresh_border()
        uncover(self._self)
        curses.doupdate()

    def hide(self):
        '''
        Hide any content in panel, or overlay if present\n
        Content in Panel and overlay are preserved'''
        self.visible = False
        if self.outline:
            self.refresh_border()
        cover(self._self)
        curses.doupdate()

class Canvas(Panel):
    '''
    Panel-like window whose purpose is to be overlaid by Pad-like windows.\n
    Canvas should not be written to, but will not stop you in the case that you do.'''
    def __init__(self, nline: int, ncols: int, beg_y: int, beg_x: int, *, outline: bool = False, overlay = None):
        self.overlay = overlay
        super().__init__(nline, ncols, beg_y, beg_x, outline)

    def noutrefresh(self):
        if self.overlay:
            if self.outline:
                self.refresh_border()
            lay(self.overlay, self._self)
    
    def set_overlay(self, overlay: Pad):
        '''
        Set an overlay to be shown and hidden with the panel.\n
        Setting an overlay does not destroy what is stored in the panel.'''
        self.overlay = overlay
    
    def remove_overlay(self):
        '''Removes overlay, and therefore, will not show overlay on .show()'''
        self.overlay = None
    
    def show(self):
        '''Display any content in panel, or overlay if present'''
        self.visible = True
        if self.outline:
            self.refresh_border()
        if self.overlay:
            lay(self.overlay, self._self)
        curses.doupdate()
