from curses import window
from typing import TypeAlias
from enum import Enum

ESC = '\x1b'
BKSP = '\x08'
ENTER = '\n'
TAB = '\t'
CTRL_BKSP = '\x17'
CTRL_SHFT_BKSP = '\x7f'

class Align(Enum):
    LEFT = 1
    RIGHT = 2
    CENTER = 3
    JUSTIFY = 4 # NOT IMPLEMENTED

class Dir(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3

PadType: TypeAlias = window
ChType: TypeAlias = str | bytes | int