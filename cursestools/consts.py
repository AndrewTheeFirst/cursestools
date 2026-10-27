from curses import window
from typing import TypeAlias
from enum import Enum, auto
from os import name as os_name

ESC = '\x1b'
ENTER = '\n'
TAB = '\t'
CTRL_BKSP = '\x17'

if os_name == "nt":
    BKSP = '\x08'
    CTRL_SHFT_BKSP = '\x7f'
else:
    BKSP = '\x7f'
    CTRL_SHFT_BKSP = '\x08'

class Align(Enum):
    LEFT = auto()
    RIGHT = auto()
    CENTER = auto()
    JUSTIFY = auto() # NOT IMPLEMENTED

class Dir(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()

class PrintMode(Enum):
    IMMEDIATE = auto()
    BY_WORD = auto()
    BY_CHAR = auto()

PadType: TypeAlias = window
ChType: TypeAlias = str | bytes | int