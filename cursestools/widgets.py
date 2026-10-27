from __future__ import annotations
import curses
from curses import window
from .utils import *
from .consts import *
from typing import Callable, Any
from abc import ABC

class _CurseWidget(ABC):
    def __init__(self):
        self._self: window = ...

    def __getattr__(self, name):
        return getattr(self._self, name)

class Page(_CurseWidget):
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

    def refresh(self) -> None:
        '''Make any update to the Console on the parent visible if not already.'''
        self.noutrefresh()
        curses.doupdate()

    def noutrefresh(self) -> None:
        '''Make any update to the Console on the parent visible if not already.'''
        lay(self._self, self.parent, self.v_shift, self.h_shift)
    
    def shift(self, dir: Dir, unit: int = 1) -> None:
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

    def reset_offset(self) -> None:
        '''Bring Console back to starting location on parent'''
        self.v_shift, self.h_shift = 0, 0

    def get_offset(self) -> None:
        return self.v_shift, self.h_shift

    def set_offset(self, *, v_shift: int = -1, h_shift: int = -1) -> None:
        if 0 < v_shift < self.max_v_shift:
            self.v_shift = v_shift
        if 0 < h_shift < self.max_h_shift:
            self.h_shift = h_shift
        
class Terminal:
    MIN_WIDTH = 3 + len("EDIT=FALSE")
    MIN_HEIGHT = 3
    
    def __init__(self, nlines, ncols, beg_y, beg_x, prompt: str = "> "):
        if (nlines < Terminal.MIN_HEIGHT) or (ncols < Terminal.MIN_WIDTH):
            raise Exception(f"TERMINAL MIN <LINES, COLS> IS <{Terminal.MIN_HEIGHT}, {Terminal.MIN_WIDTH}>")
        self.border = curses.newwin(nlines, ncols, beg_y, beg_x)
        self._self = curses.newwin(nlines - 2, ncols - 2, beg_y + 1, beg_x + 1)
        self.prompt = prompt
        self.max_chars = (ncols - 2) * (nlines - 2) - len(self.prompt)
        self.message = ""
        self.last_print = ""
        self.submitted = False
        self.editing = True
        self.noutrefresh()
        self.binds: dict[str, Callable[[], None]] = {BKSP: self._delete,
                                                     CTRL_BKSP: self._delete_last_word,
                                                     CTRL_SHFT_BKSP: self._delete_all,
                                                     ENTER: self._submit}
        self.commands: dict[str, Callable[[], None]] = {}

    def noutrefresh(self):
        self.border.box()
        self.border.addstr(0, 2, f"EDIT={repr(self.editing).upper()}", curses.A_STANDOUT)
        self._refresh_term()
        self.border.noutrefresh()
        self._self.noutrefresh()

    def refresh(self) -> None:
        self.noutrefresh()
        curses.doupdate()

    def _submit(self):
        self.submitted = True
        action = self.commands.get(self.peek_text(), None)
        if not action is None:
            action()

    def add_command(self, command: str, action: Callable[[], None]) -> None:
        self.commands[command] = action

    def rm_command(self, command: str) -> None:
        self.commands.pop(command)
    
    def _toggle_mode(self):
        self.editing = not self.editing
    
    def _delete(self):
        if len(self.message) > 0:
            self.message = self.message[:-1]
            self._update_term()
    
    def _delete_all(self):
        self.message = ''
        self._update_term()

    def _delete_last_word(self):
        words = self.message.split()
        if words:
            words.pop()
            self.message = ' '.join(words) + ' '
            if self.message == ' ':
                self.message = ''
        self._update_term()

    def _update_term(self, key: str = ""):
        if key and key.isprintable() and len(self.message) < self.max_chars:
            self.message += key
        if self.message != self.last_print:
            self._self.clear()
            self._refresh_term()
            self.last_print = self.message
    
    def _refresh_term(self):
        self._self.clear()
        if len(self.message) == self.max_chars:
            # prevents OOB error due to curses' automatic wrap flag
            try:
                self._self.addstr(0, 0, self.prompt + self.message)
            except curses.error:
                pass
        else:
            self._self.addstr(0, 0, self.prompt + self.message)

    def getkey(self) -> ChType:
        return self._self.getkey()

    def proc_key(self, key: ChType) -> ChType:
        if key == TAB:
            self._toggle_mode()
            self.refresh()
        elif self.editing:
            action = self.binds.get(key,lambda: self._update_term(key))
            action()
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

    def _get_x_offset_center(self, text_len: int, space_width: int):
        border_offset_x = 1 if self.outline else 0
        return border_offset_x + (space_width - text_len) // 2
    
    def _get_x_offset_right(self, text_len: int, space_width: int):
        border_offset_x = 1 if self.outline else 0
        return border_offset_x + space_width - text_len
    
    def _get_x_offset_left(self, text_len: Any, space_width: Any):
        border_offset_x = 1 if self.outline else 0
        return border_offset_x
    
    def _get_y_offset(self, text: str):
        current_y = 1 if self.outline else 0
        if not self.v_centered:
            return current_y
        min_nlines = self._get_min_nlines(text)
        if self.height < min_nlines:
            return current_y
        return current_y + (self.height - self._get_min_nlines(text)) // 2
        
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

    def print(self, text: str) -> None:
        current_y = self._get_y_offset(text)
        current_line_length = 0
        current_line = ""
        self.erase()
        words = text.split()
        for index, word in enumerate(text.split()):
            if current_y > self.height:
                return " ".join(words[index - 1:])
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
                offset_x = self.get_offset_x(current_line_length, self.width)
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
    def __init__(self, nline: int, ncols: int, beg_y: int, beg_x: int, *, outline: bool = False):
        self.outline = outline
        if self.outline:
            self.border = curses.newwin(nline, ncols, beg_y, beg_x)
            self._self = self.border.subwin(nline - 2, ncols - 2, beg_y + 1, beg_x + 1)
        else:
            self._self = curses.newwin(nline, ncols, beg_y, beg_x)
        self.visible = True
    
    def _refresh_border(self):
        self.border.box()
        self.border.noutrefresh()

    def noutrefresh(self):
        if self.outline:
            self._refresh_border()
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
            self._refresh_border()
        uncover(self._self)
        curses.doupdate()

    def hide(self):
        '''
        Hide any content in panel, or overlay if present\n
        Content in Panel and overlay are preserved'''
        self.visible = False
        if self.outline:
            self._refresh_border()
        cover(self._self)
        curses.doupdate()

class Canvas(Panel):
    def __init__(self, nline: int, ncols: int, beg_y: int, beg_x: int, *, outline: bool = False, overlay = None):
        self.overlay = overlay
        super().__init__(nline, ncols, beg_y, beg_x, outline=outline)

    def noutrefresh(self):
        if self.outline:
            self._refresh_border()
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
            self._refresh_border()
        if self.overlay:
            lay(self.overlay, self._self)
        curses.doupdate()
