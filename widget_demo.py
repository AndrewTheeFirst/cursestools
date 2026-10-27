from __future__ import annotations
from cursestools import *
try:
    from cursestools.cursestools import Page, Dir, Terminal, PrintMode, get_stdscr, TextBox, Panel, Canvas, init_curses, deinit_curses, Align
except Exception:
    ...
from curses import *
import curses
from time import sleep

def _make_letter_generator():
    a_ord = ord('A')
    upper = [chr(a_ord + letter_offset) for letter_offset in range(26)]
    lower = [chr(a_ord + letter_offset) for letter_offset in range(26 + 6, 26 + 6 + 26)]
    upper + lower
    while True:
        for entry in lower + upper:
            yield entry

def _pause(msg: str = "", wait_for_enter: bool = True):
    global text_area, max_y
    text_area.erase()
    if msg:
        text_area.addstr(0, 0, msg.ljust(max_y), curses.A_NORMAL)
        text_area.refresh()

        text_area.erase()
        text_area.addstr(0, 0, msg.ljust(max_y), curses.A_STANDOUT)
        text_area.refresh()
        sleep(0.25)

        text_area.erase()
        text_area.addstr(0, 0, msg.ljust(max_y), curses.A_NORMAL)
    text_area.refresh()
    if wait_for_enter:
        text_area.getch()

def test_page():
    global stdscr
    parent_window = newwin(10, 15, 8, 2)
    page = Page(parent_window, multiplier=2, width=60)

    letter_gen = _make_letter_generator()
    for y in range(page.getmaxyx()[0] - 1):
        for x in range(page.getmaxyx()[1]):
            if x == 0:
                page.addch(y, x, str(y)[len(str(y)) - 1])
            else:
                page.addch(y, x, next(letter_gen))
    page.refresh()

    _pause("Pages can be made as big as needed, and be shifted as desired.", wait_for_enter=True)
    for dir in [Dir.UP, Dir.DOWN]:
        _pause(f"{dir}", wait_for_enter=False)
        for _ in range(page.getmaxyx()[0] - 1):
            page.shift(dir)
            page.refresh()
            sleep(0.1)
    for dir in [Dir.LEFT, Dir.RIGHT]:
        _pause(f"Pages can be made as big as needed, and be simply scrolled as desired: {dir}", wait_for_enter=False)
        for _ in range(page.getmaxyx()[1]):
            page.shift(dir)
            page.refresh()
            sleep(0.02)

def test_terminal():
    global stdscr
    _pause("Terminals allows for custom commands.")
    sleep(2)
    _pause("Try typing the ls or pwd and press enter. Press Tab to enable/disable typing. Type exit and enter to continue.", wait_for_enter=False)
    terminal = Terminal(3, 50, 0, 3)
    terminal.refresh()

    terminal.add_command("ls",      lambda: _pause("ls command was recognized!", wait_for_enter=False))
    terminal.add_command("pwd",     lambda: _pause("pwd command was recognized!", wait_for_enter=False))
    terminal.add_command("exit",    lambda: exec("raise Exception"))
    
    while True:
        key = terminal.getkey()
        try:
            terminal.proc_key(key)
        except Exception:
            break

def test_textbox():
    textbox = TextBox(7, 50, 10, 50, outline=True)
    textbox.set_printing_configuration(
        printing_mode=PrintMode.BY_CHAR,
        delay=0.01,
        pause_multiplier=50
    )
    _pause("Text can be printed into a Textbox instantly, or slowly.", wait_for_enter=False)
    remaining_text = textbox.print("Lines of amber text cascaded down the terminal screen, reflecting softly in the engineer's glasses as they searched for the elusive memory leak. Every keystroke echoed faintly in the empty room, a rhythmic testament to the quiet focus required to untangle complex systems. Outside, the city had long since gone to sleep, leaving only the glowing monitors and the steady pulse of network traffic to keep watch over the digital architecture.")
    _pause("And text that doesnt fit, is returned to be printed again.", wait_for_enter=False)
    while remaining_text:
        sleep(1)
        remaining_text = textbox.print(remaining_text)
    textbox.set_printing_configuration(
        printing_mode=PrintMode.IMMEDIATE,
        v_centered=True,
        align=Align.CENTER
    )
    textbox.print("Find definitions and references for functions and other symbols in this file by clicking a symbol below or in the code.")
    _pause("Text can also be centered vertically, horizontally, or right-justified if desired.")

def test_panel():
    plain = Panel(5, 30, 20, 60)
    plain.addstr(0, 0, "Plain panel (no outline)")
    plain.addstr(1, 0, "5x30 usable area")

    boxed = Panel(7, 30, 1, 60, outline=True)
    boxed.addstr(0, 0, "Outlined panel")
    boxed.addstr(1, 0, "5x28 usable area")

    plain.refresh()
    boxed.refresh()
    _pause("Panels are windows whose visibility can be toggled.")

    for _ in range (4):
        plain.toggle()
        boxed.toggle()
        _pause()

def test_canvas():
    pad_a = newpad(8, 18)
    pad_b = newpad(8, 18)
    for y in range(7):
        for x in range(18):
                pad_a.addch(y, x, 'A' if (x + y) % 2 else '.')
                pad_b.addch(y, x, 'B' if y % 2 else '#')

    canvas = Canvas(10, 15, 7, 35, outline=True)
    canvas.refresh()
    _pause("Canvas' are a subclass of Panels which may swap overlays.")

    canvas.set_overlay(pad_a)
    canvas.show()
    _pause()
    canvas.toggle()
    _pause()
    canvas.toggle()
    _pause()

    canvas.set_overlay(pad_b)
    canvas.show()
    _pause()
    canvas.toggle()
    _pause()
    canvas.toggle()

    _pause("Overlays can be swapped easily.", wait_for_enter=False)
    for i in range(8):
        canvas.set_overlay(pad_a if i % 2 == 0 else pad_b)
        canvas.show()
        sleep(0.3)

def main():
    test_page()
    test_terminal()
    test_canvas()
    test_panel()
    test_textbox()
    _pause("Demo Complete.")

if __name__ == "__main__":
    exception_str = ''
    try:
        init_curses()
        stdscr = get_stdscr()
        max_y, max_x = stdscr.getmaxyx()
        text_area = newwin(1, max_x, max_y - 1, 0)
        main()
    except Exception as e:
        exception_str = f"An exception has occured: {e}"
    finally:
        deinit_curses()
        if exception_str:
            print(exception_str)
