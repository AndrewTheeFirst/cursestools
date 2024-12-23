from curses import window
from typing import overload, TypeAlias
from enum import Enum

Pad = window
_ChType: TypeAlias = str | bytes | int

ESC = ...
BKSP = ...
ENTER = ...
CTRL_BKSP = ...

class Dir(Enum):
    UP = ...
    DOWN = ...
    LEFT = ...
    RIGHT = ...

def draw_button(beg_y: int, beg_x: int, height: int, width: int, window: window, text: str = "") -> None: ...
def is_printable(char: _ChType) -> bool: ...
def reprint_win(window: window) -> None: ...
def lay(content: Pad, window: window) -> None: ...
@overload
def cover(window: window) -> None: ...
@overload
def cover(window: window, veil: Pad) -> None: ...
def uncover(window: window) -> None:...
@overload
def wprint(self, window: window, message: str) -> None: ...
@overload
def wprint(window: window, y: int, x: int, message: str) -> None: ...
@overload
def wread(window: window, message: str, speed: int = 1) -> None: ...
@overload
def wread(window: window, y: int, x: int, message: str, speed: int = 1) -> None: ...

class _CurseWidget:
    def __init__(self): ...
    def __getattr__(self, name: str) -> object: ...
    def getmaxyx(self) -> tuple[int, int]: ...
    def getbegyx(self) -> tuple[int, int]: ...
    def refresh(self) -> None: ...
    def noutrefresh(self) -> None: ...
    @overload
    def chgat(self, attr: int) -> None: ...
    @overload
    def chgat(self, num: int, attr: int) -> None: ...
    @overload
    def chgat(self, y: int, x: int, attr: int) -> None: ...
    @overload
    def chgat(self, y: int, x: int, num: int, attr: int) -> None: ...
    @overload
    def addstr(self, str: str, attr: int = ...) -> None: ...
    @overload
    def addstr(self, y: int, x: int, str: str, attr: int = ...) -> None: ...
    @overload
    def addch(self, ch: _ChType, attr: int = ...) -> None: ...
    @overload
    def addch(self, y: int, x: int, ch: _ChType, attr: int = ...) -> None: ...

class Console(_CurseWidget): # pad based widget
    def __init__(self, parent: window, multiplier: int = 2): ...
    def out(self, text: str) -> None: ...
    def cls(self) -> None: ...
    def noutrefresh(self, pminrow: int, pmincol: int, sminrow: int, smincol: int, smaxrow: int, smaxcol: int) -> None: ...
    def shift(self, dir: Dir, unit: int = 1) -> None: ...
    def reset_offset(self) -> None: ...
    def get_offset(self) -> tuple[int, int]: ...

class TextBox(_CurseWidget):
    def __init__(self, nline: int, ncols: int, beg_y: int, beg_x: int): ...
    def proc_key(self, key: _ChType) -> None: ...
    def clear_text(self) -> None: ...
    def get_text(self) -> str: ...
    def peek_text(self) -> str: ...

class Panel(_CurseWidget):
    def __init__(self, nline: int, ncols: int, beg_y: int, beg_x: int, outline: bool = False):
        self.visible: bool = ...
    def set_overlay(self, overlay: Pad) -> None: ...
    def remove_overlay(self) -> None: ...
    def toggle(self) -> None: ...
    def show(self) -> None: ...
    def hide(self) -> None: ...

