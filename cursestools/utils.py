import curses
from curses import window
from .consts import PrintMode
from .widgets import PadType
from time import sleep
from curses.textpad import rectangle
from typing import overload
from os import name as os_name

_stdscr: window =  None
_pausechars = ", ; . ? !".split(' ')
_curses_is_init: bool = False

def _check_curses():
    global _curses_is_init
    if not _curses_is_init:
        raise Exception("Curses must be initialized.")
    
_curses_initscr = curses.initscr
_curses_endwin = curses.endwin

def _initscr_patch():
    global _curses_is_init, _stdscr
    _stdscr = _curses_initscr()
    _curses_is_init = True

def _endwin_patch():
    global _curses_is_init
    _curses_endwin()
    _curses_is_init = False
 
curses.initscr = _initscr_patch
curses.endwin = _endwin_patch

def init_curses() -> None:
    if not _curses_is_init:
        curses.initscr()
    curses.noecho()
    curses.curs_set(0)
    curses.cbreak()
    if os_name != "nt":
        curses.set_escdelay(20)

def deinit_curses() -> None:
    global _curses_is_init
    if _curses_is_init:
        curses.echo()
        curses.nocbreak()
        curses.endwin()

def get_stdscr() -> window:
    global _stdscr
    _check_curses()
    return _stdscr

def draw_box(window: window, height: int, width: int, beg_y: int, beg_x: int):
    '''Draw a box at specified at (beg_y, beg_x) with specified (height, width)'''
    rectangle(window, beg_y, beg_x, beg_y + height - 1, beg_x + width - 1)

def draw_button(window: window, height: int, width: int, beg_y: int, beg_x: int, text: str = ""):
    '''Draw a button with optional text (centered)'''
    draw_box(window, height, width, beg_y, beg_x)
    start_x = beg_x + (width - len(text)) // 2
    start_y = beg_y + (height - 1) // 2
    window.addstr(start_y, start_x, text)

def reprint_win(window: window): # (MAY BRIGHTEN DUE TO BOLD)
    '''Useful for overlaying any temporary pad'''
    max_y, max_x = window.getmaxyx()
    window.resize(max_y + 1, max_x + 1)
    (window.addch(y, x, window.inch(y, x), curses.A_BOLD) for y in range(max_y) for x in range(max_x))
    window.resize(max_y, max_x)

def lay(content: window, window: window, coffset_y = 0, coffset_x = 0):
    '''Overlays as much content as can fit in a window (only calls noutrefresh on content)'''
    beg_y, beg_x = window.getbegyx()
    max_y, max_x = window.getmaxyx()
    content.noutrefresh(coffset_y, coffset_x, beg_y, beg_x, beg_y + max_y - 1, beg_x + max_x - 1)

@overload
def wprint(self, window: window, message: str, *, print_mode = PrintMode.IMMEDIATE, delay: float = 0.1) -> None: ...
@overload
def wprint(window: window, y: int, x: int, message: str, *, print_mode = PrintMode.IMMEDIATE, delay: float = 0.1) -> None: ...

def wprint(window: window, arg_1: str | int, x: int = -1, string: str = "", *, print_mode: PrintMode = PrintMode.IMMEDIATE, delay: float = 0.1, pause_multiplier: float = 2) -> None:
    '''Add string to window with automatic refresh'''
    if not string: # the first arg is message
        string = arg_1
    else: # the first two args are starting coords
        window.move(arg_1, x)
    match (print_mode):
        case PrintMode.IMMEDIATE:
            window.addstr(string)
            window.refresh()
        case PrintMode.BY_WORD:
            words = string.split()
            if not words:
                return
            word = words[0]
            window.addstr(word)
            window.refresh()
            sleep(delay * pause_multiplier if word[len(word) - 1] in _pausechars else delay)
            for word_index in range(1, len(words)):
                word = words[word_index]
                window.addstr(" " + word)
                window.refresh()
                sleep(delay * pause_multiplier if word[len(word) - 1] in _pausechars else delay)
        case PrintMode.BY_CHAR:
            for letter_index in range(len(string)):
                letter = string[letter_index]
                window.addch(letter)
                window.refresh()
                sleep(delay * pause_multiplier if letter in _pausechars else delay)

@overload
def cover(window: window) -> None: ...
@overload
def cover(window: window, veil: PadType) -> None: ...
def cover(window: window, veil: PadType = None):
    '''
    cover/hide a window via a temporary pad -- "veil"\n
    cover is destructive and will clear and deallocate veil.'''
    if veil is None:
        veil = curses.newpad(*window.getmaxyx())
    lay(veil, window)
    veil.clear()
    del veil

def uncover(window: window):
    '''uncover/unhide a window'''
    reprint_win(window)
    window.noutrefresh()