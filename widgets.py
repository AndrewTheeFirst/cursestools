import curses
from curses import window
from .utils import *
from .consts import *
from threading import Event
from typing import Literal

class _CurseWidget:
    '''Emulate inheritance from curses.window which has @final decorator.'''
    def __init__(self):
        self._self: window = ...

    def __getattr__(self, name):
        return getattr(self._self, name)

class Page(_CurseWidget):
    '''A Pad-Like widget to abstract scrolling content that cannot all fit in the window at once.'''
    def __init__(self, parent: window, *, multiplier = 1, height = 0, width = 0):
        '''
        Initialize a Page object to be "laid" onto a parent window.\n
        If a height or width is set, the multiplier will be ignored for that dimension.'''
        self.parent = parent
        self.reset_offset()
        par_h, par_w = parent.getmaxyx()
        if not height:
            height = par_h * multiplier
        if not width:
            width = par_w * multiplier
        self._self: window = curses.newpad(height, width)
        self.max_v_shift = height - par_h
        self.max_h_shift = width - par_w

    def refresh(self):
        '''Make any update to the Console on the parent visible if not already.'''
        lay(self._self, self.parent, self.v_shift, self.h_shift)
        curses.doupdate()
    
    def shift(self, dir: Dir, unit: int = 1):
        '''Shift the console in "dir" directiion "unit" units.'''
        match (dir):
            case Dir.UP:
                self.v_shift += unit
                if self.v_shift > self.max_v_shift:
                    self.v_shift = self.max_v_shift
            case Dir.DOWN: 
                self.v_shift -= unit
                if self.v_shift < 0:
                    self.v_shift = 0
            case Dir.LEFT:
                self.h_shift += unit
                if self.h_shift > self.max_h_shift:
                    self.h_shift = self.max_h_shift
            case Dir.RIGHT:
                self.h_shift -= unit
                if self.h_shift < 0:
                    self.h_shift = 0
    
    def reset_offset(self):
        '''Bring Console back to starting location on parent'''
        self.v_shift, self.h_shift = 0, 0

    def get_offset(self):
        return self.v_shift, self.h_shift

    def out(self, text: str, end = '\n'):
        '''print to Console and update the screen'''
        self._self.addstr(text + end)
        self.refresh()

    def cls(self):
        '''Clear the Console and update the screen'''
        self._self.clear()
        cover(self.parent)
        
class Terminal(_CurseWidget):
    '''A Terminal to display, process, and submit keystrokes.'''
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
    '''A class to automatically format text in a window.'''
    def __init__(self, nlines: int, ncols: int, text: str = "", \
                    *, alignment: Align = Align.LEFT, v_centered: bool = False):
        self.set_size(nlines, ncols)
        self.set_text(text)
        self.set_alignment(alignment, v_centered=v_centered)

    def set_text(self, text: str):
        self.text = text

    def set_alignment(self, align: Align = None, *, v_centered: bool | None = None):
        if not v_centered is None:
            self.v_centered = v_centered
        if not align is None:
            self.alignment = align

    def set_size(self, height: int, width: int):
            self.nlines = height
            self.ncols = width
            self.width = width - 2

    def print_textbox(self, parent: window, beg_y: int, beg_x: int):
        self.verify_nlines()
        parent.vline(beg_y, beg_x, curses.ACS_VLINE, self.nlines)
        parent.vline(beg_y, beg_x + self.ncols - 1, curses.ACS_VLINE, self.nlines)
        if self.v_centered:
            beg_y = beg_y + (self.nlines - self.min_nlines) // 2
        self.write(parent, beg_y, beg_x)

    def read_textbox(self, parent: window, beg_y: int, beg_x: int,\
                     mode: Literal["WORD"] | Literal["CHAR"] = "CHAR", timeout: float = 0.05):
        self.verify_nlines()
        parent.vline(beg_y, beg_x, curses.ACS_VLINE, self.nlines)
        parent.vline(beg_y, beg_x + self.ncols - 1, curses.ACS_VLINE, self.nlines)
        if self.v_centered:
            beg_y = beg_y + (self.nlines - self.min_nlines) // 2
        self.read(parent, beg_y, beg_x, mode, timeout)

    def verify_nlines(self):
        self.min_nlines = self.get_min_nlines()
        if self.nlines < self.min_nlines:
            raise Exception(f"Textbox MUST have MINIMUM {self.min_nlines} LINES given # COLS")

    def get_min_nlines(self):
        if len(self.text) == 0:
            return 0
        nlines = 1
        current_length = 0
        for word in self.text.split():
            word_length = len(word)
            if current_length + 1 + word_length > self.width:
                nlines += 1
                current_length = word_length
            else:
                current_length += 1 + word_length
        return nlines

    def write(self, parent: window, beg_y: int, beg_x: int):
            current_line_length = 0
            current_line = []
            current_y = beg_y

            for word in self.text.split():
                word_length = len(word)
                if current_line_length + 1 + word_length > self.width:
                    parent.addstr(current_y, beg_x + 1, ' ' * self.width) # CLEARS LINE IN CASE OF LEAKAGE FROM PREV PRINT
                    self.format(parent, current_y, beg_x + 1, current_line)
                    current_line = [word]
                    current_line_length = word_length
                    current_y += 1
                else:
                    current_line.append(word)
                    current_line_length += 1 + word_length

            if current_line:
                self.format(parent, current_y, beg_x + 1, current_line)

    def read(self, parent: window, beg_y: int, beg_x: int,\
                     mode: Literal["WORD"] | Literal["CHAR"] = "CHAR", timeout: float = 0.05):
        if mode == "WORD":
            builder = []
            itera = self.text.split()
        elif mode == "CHAR":
            builder = ""
            itera = self.text
        else:
            raise Exception("Invalid Mode - Valid Chunk Modes: 'CHAR', 'WORD'")
        for block in itera:
            if mode == "WORD":
                builder.append(block)
                text = " ".join(builder)
                self.set_text(text)
            if mode == "CHAR":
                builder += block
                self.set_text(builder)
            self.write(parent, beg_y, beg_x)
            parent.refresh()
            sleep(timeout)

    def format(self, parent: window, y: int, x: int, line: list[str]):
        # writing in bottom left corner will automatically wrap to next line
        # which may be out of bounds causing exception.
        # we will just except it here and pass
        try:
            text = " ".join(line)
            line_length = len(text)
            parent.addstr(y, x + self.get_offset(line_length), text)
        except curses.error:
            pass 

    def get_offset(self, line_length: int):
        match (self.alignment):
            case Align.RIGHT:
                return (self.width - line_length)
            case Align.CENTER:
                return (self.width - line_length) // 2
            case Align.LEFT:
                ...
        return 0
      
class Panel(_CurseWidget):
    '''An extenstion to curses.window object, whose visibility may be toggled.'''
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
    
    def set_overlay(self, overlay: PadType):
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
