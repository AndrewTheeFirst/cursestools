from curses import window
from typing import TypeAlias
from enum import Enum

ESC = '\x1b'
BKSP = '\x08'
ENTER = '\n'
CTRL_BKSP = '\x17'

class Align(Enum):
    LEFT = 0
    CENTER = 1
    JUSTIFY = 2
    RIGHT = 3

class Dir(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3

Pad = window
ChType: TypeAlias = str | bytes | int