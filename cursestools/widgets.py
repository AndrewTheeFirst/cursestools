from __future__ import annotations
import curses
from curses import window
from .utils import *
from .consts import *
from typing import Literal, Callable
from enum import Enum, auto

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
        self.noutrefresh()
        curses.doupdate()

    def noutrefresh(self):
        '''Make any update to the Console on the parent visible if not already.'''
        lay(self._self, self.parent, self.v_shift, self.h_shift)
    
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
    
    def get_parent_window(self) -> _CurseWidget | window:
        return self.parent

    def reset_offset(self):
        '''Bring Console back to starting location on parent'''
        self.v_shift, self.h_shift = 0, 0

    def get_offset(self):
        return self.v_shift, self.h_shift

    def set_offset(self, *, v_shift: int = -1, h_shift: int = -1):
        if 0 < v_shift < self.max_v_shift:
            self.v_shift = v_shift
        if 0 < h_shift < self.max_h_shift:
            self.h_shift = h_shift
    
    def clear(self):
        self._self.clear()
        
class Terminal(_CurseWidget):
    '''A Terminal to display, process, and submit keystrokes.'''
    min_width = 3 + len("EDIT=FALSE")
    min_height = 3
    
    def __init__(self, nlines, ncols, beg_y, beg_x, default: str = "> "):
        if (nlines < Terminal.min_height) or (ncols < Terminal.min_width):
            raise Exception(f"TERMINAL MIN <LINES, COLS> IS <{Terminal.min_height}, {Terminal.min_width}>")
        self.border = curses.newwin(nlines, ncols, beg_y, beg_x)
        self._self = curses.newwin(nlines - 2, ncols - 2, beg_y + 1, beg_x + 1)
        self.default = default
        self.max_chars = (ncols - 2) * (nlines - 2) - len(self.default)
        self.message = ""
        self.last_print = ""
        self.submitted = False
        self.editing = True
        self.noutrefresh()
        self.binds: dict[str, Callable[[], None]] = {BKSP: self.delete,
                                                     CTRL_BKSP: self.delete_last_word,
                                                     CTRL_SHFT_BKSP: self.delete_all,
                                                     ENTER: self.submit}

    def noutrefresh(self):
        self.border.box()
        self.border.addstr(0, 2, f"EDIT={repr(self.editing).upper()}", curses.A_STANDOUT)
        self._print()
        self.border.noutrefresh()
        self._self.noutrefresh()

    def refresh(self):
        self.noutrefresh()
        curses.doupdate()

    def submit(self):
        self.submitted = True
    
    def toggle_mode(self):
        self.editing = not self.editing
    
    def delete(self):
        if len(self.message) > 0:
            self.message = self.message[:-1]
            self.print()
    
    def delete_all(self):
        self.message = ''
        self.print()

    def delete_last_word(self):
        words = self.message.split()
        if words:
            words.pop()
            self.message = ' '.join(words) + ' '
            if self.message == ' ':
                self.message = ''
        self.print()

    def print(self, key: str = ""):
        if key and key.isprintable() and len(self.message) < self.max_chars:
            self.message += key
        if self.message != self.last_print:
            self._self.clear()
            self._print()
            self.last_print = self.message
    
    def _print(self):
        self._self.clear()
        if len(self.message) == self.max_chars:
            # prevents OOB error due to curses' automatic wrap flag
            try:
                self._self.addstr(0, 0, self.default + self.message)
            except curses.error:
                pass
        else:
            self._self.addstr(0, 0, self.default + self.message)
    
    def proc_key(self, key: ChType) -> ChType:
        if key == TAB:
            self.toggle_mode()
            self.refresh()
        elif self.editing:
            self.binds.get(key, lambda: self.print(key))()
        else: # key ignored
            return key
        self.refresh()
        return ''

    def get_text(self) -> str:
        '''Waits for submission event then returns whats stored in the message field'''
        if self.submitted:
            self.submitted = False
            return self.message
        else:
            return ''

    def peek_text(self) -> str:
        '''Return text currently stored in textbox'''
        return self.message

class TextBox:
    def __init__(self, nlines: int, ncols: int, beg_y: int, beg_x: int, *, outline: bool = False):
        self.beg_y: int
        self.beg_x: int
        self.nlines: int
        self.ncols: int
        self._window: window
        self.outline: bool
        self.v_centered: bool
        self.alignment: Align
        self.get_offset_x: Callable[[int, int], int]
        self.printing_mode: PrintMode
        self.delay: float
        self.pause_multiplier: int
        
        self.outline = outline
        self._window = curses.newwin(nlines, ncols, beg_y, beg_x)
        self.resize(nlines, ncols)
        self.mvwin(beg_y, beg_x)
        self.set_printing_configuration(align=Align.LEFT,
                                        v_centered=False,
                                        printing_mode=PrintMode.IMMEDIATE,
                                        delay=0.1,
                                        pause_multiplier=2)

        if self.outline:
            self.border = curses.newwin(nlines, ncols, beg_y, beg_x)
            self._self = self.border.subwin(nlines - 2, ncols - 2, beg_y + 1, beg_x + 1)
        else:
            self._self = curses.newwin(nlines, ncols, beg_y, beg_x)

    def resize(self, nlines: int, ncols: int) -> None:
        self.nlines, self.height = nlines, nlines
        self.ncols, self.width = ncols, ncols
        if self.outline:
            self.height = nlines - 2
            self.width = ncols - 2
        self._window.resize(nlines, ncols)

    def mvwin(self, y: int, x: int) -> None:
        self._window.erase()
        self._window.refresh()
        self.beg_y, self.beg_x = y, x

        self._window.mvwin(y, x)
        self._window.border()
        self._window.refresh()

    def erase(self) -> None:
        self._window.erase()
        if self.outline:
            self._window.border()
        self._window.refresh()

    def _get_x_offset_center(self, text_len, space_width):
        border_offset_x = 1 if self.outline else 0
        return border_offset_x + space_width - text_len
    
    def _get_x_offset_right(self, text_len, space_width):
        border_offset_x = 1 if self.outline else 0
        return border_offset_x + (space_width - text_len) // 2
    
    def _get_x_offset_left(self, text_len, space_width):
        border_offset_x = 1 if self.outline else 0
        return border_offset_x

    def set_printing_configuration(self, *, align: Align | None = None, v_centered: bool | None = None,\
                                   printing_mode: PrintMode | None = None, delay: float | None = None, pause_multiplier: int | None = None) -> None:
        if not v_centered is None:
            self.v_centered = v_centered
        if not align is None:
            self.alignment = align
        match (self.alignment):
            case Align.CENTER:
                self.get_offset_x = self._get_x_offset_center
            case Align.RIGHT:
                self.get_offset_x = self._get_x_offset_right
            case Align.LEFT:
                self.get_offset_x = self._get_x_offset_left
        if not printing_mode is None:
            self.printing_mode = printing_mode
        if not delay is None:
            self.delay = delay
        if not pause_multiplier is None:
            self.pause_multiplier = pause_multiplier

    def _get_min_nlines(self, text: str):
        current_y = 0
        if self.outline:
            current_y += 1
        current_line_length = 0
        current_line = ""
        self.erase()
        for word in text.split():
            word_length = len(word)
            while(word_length > self.width):
                if current_line_length == 0:
                    fitting_text = word[:self.width]
                    word = word[self.width:]
                    current_y += 1
                else:
                    remaining_space = self.width - word_length
                    fitting_text = word[:word[remaining_space]]
                    current_line = current_line + ' '  + fitting_text
                    word = word[self.width:]
                    current_y += 1
                    current_line = ''
                word_length = len(word)
            if current_line_length == 0:
                current_line = word
                current_line_length = word_length
                continue
            prospective_length = current_line_length + 1 + word_length
            if prospective_length < self.width:
                current_line = current_line + ' ' + word
                current_line_length = prospective_length
            elif prospective_length == self.width:
                current_line = current_line + ' ' + word
                current_line = ""
                current_line_length = 0
                current_y += 1
            else:
                current_line = word
                current_line_length = word_length
                current_y += 1
        return current_y

    def write(self, text: str) -> None:
        min_nlines = self._get_min_nlines(text)
        if self.height < min_nlines:
            raise Exception(f"Textbox MUST have MINIMUM {min_nlines + 2 if self.outline else min_nlines} LINES given # COLS")
        current_y = (self.height - min_nlines) // 2 if self.v_centered else 0
        if self.outline:
            current_y += 1
        current_line_length = 0
        current_line = ""
        self.erase()
        for word in text.split():
            if current_y > self.height:
                return
            word_length = len(word)
            while(word_length > self.width): # word is too large -- must be split across lines
                if current_line_length == 0: # First word on line. Add what fits.
                    fitting_text = word[:self.width]
                    offset_x = self.get_offset_x(self.width, self.width)
                    wprint(self._window, current_y, offset_x, fitting_text,\
                            print_mode=self.printing_mode, delay=self.delay, pause_multiplier=self.pause_multiplier)
                    word = word[self.width:]
                    current_y += 1
                else: # Second word on line, add space and what fits.
                    remaining_space = self.width - word_length
                    fitting_text = word[:word[remaining_space]]
                    current_line = current_line + ' '  + fitting_text
                    offset_x = self.get_offset_x(self.width, self.width)
                    wprint(self._window, current_y, offset_x, current_line,\
                            print_mode=self.printing_mode, delay=self.delay, pause_multiplier=self.pause_multiplier)
                    word = word[self.width:]
                    current_y += 1
                    current_line = ''
                word_length = len(word)
            if current_line_length == 0: # First word on line. Add to line.
                current_line = word
                current_line_length = word_length
                continue
            prospective_length = current_line_length + 1 + word_length
            if prospective_length < self.width: # 
                current_line = current_line + ' ' + word
                current_line_length = prospective_length
            elif prospective_length == self.width: # Word will complete the line.
                current_line = current_line + ' ' + word
                offset_x = self.get_offset_x(prospective_length, self.width)
                wprint(self._window, current_y, offset_x, current_line,\
                       print_mode=self.printing_mode, delay=self.delay, pause_multiplier=self.pause_multiplier)
                current_line = ""
                current_line_length = 0
                current_y += 1
            else: # Word does not fit on line. Add it to next line.
                offset_x = self.get_offset_x(prospective_length, self.width)
                wprint(self._window, current_y, offset_x, current_line,\
                       print_mode=self.printing_mode, delay=self.delay, pause_multiplier=self.pause_multiplier)
                current_line = word
                current_line_length = word_length
                current_y += 1 
        if current_line:
            offset_x = self.get_offset_x(len(current_line), self.width)
            wprint(self._window, current_y, offset_x, current_line,\
                       print_mode=self.printing_mode, delay=self.delay, pause_multiplier=self.pause_multiplier)      

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
        if self.outline:
            self.refresh_border()
        if self.overlay:
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
