import curses
from enum import Enum

ANSI = "\x1b[{}m"
class _Color(Enum):
    RED = ANSI.format(31)
    GREEN = ANSI.format(32)
    YELLOW = ANSI.format(33)
    BLUE = ANSI.format(34)
    CLEAR = ANSI.format(0)

class Color:
    cwcisinit = False
    def __init__(self):
        if curses.has_colors():
            curses.start_color()
            Color.cwcisinit = True
            self.colors = Enum()
            self.setup_colors()
    
    def setup_colors(self, offset: int = 1):
        for index, color, in enumerate(_Color):
            curses_color = getattr(curses, f"COLOR_{color.name}")
            curses.init_pair(offset + index, curses_color)
    
    def start_color(self):
        pass

    def end_color(self):
        pass