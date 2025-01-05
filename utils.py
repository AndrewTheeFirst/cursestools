import curses
from curses import window
from .consts import ChType, PadType
from time import sleep
from curses.textpad import rectangle

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

def wprint(window: window, arg_1: str | int, x: int = -1, message: str = ""):
    '''Add string to window with automatic refresh'''
    if not message: # the first arg is message
        message = arg_1
    else: # the first two args are coords
        window.move(arg_1, x)
    window.addstr(message)
    window.refresh()

def wread(window: window, arg_1: str | int, arg_2: int = 1, message: str = "", speed = 1):
    '''
    Add string to window with automatic refresh.\n
    Prints one char at a time to emulate a typed look'''
    if not message: # the first two args is message and speed respectively
        speed = arg_2
        message = arg_1
    else: # the first two args are coords
        window.move(arg_1, arg_2)
    rate = 0.1/speed
    for char in message:
        sleep(rate)
        window.addch(char)
        window.refresh()

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