import copy
import json
import time
import typing

import random
import ansi
from non_blocking_input import nbprepare, nbclose
import atexit
import sys, os

nb = nbprepare()
atexit.register(nbclose)

l_snake = []
dangerous_grids = set()

bw = 2

_size: typing.Optional[typing.Tuple] = None
_display_size: typing.Optional[typing.Tuple] = None
def get_size() -> typing.Tuple:
    global _size
    if _size is None:
        change_size()
    return _size

_debug = False
_debug_buffer = []
_MAX_DEBUG_BUFFER = 2
def debug(*args, **kwargs):
    global _debug_buffer
    if _debug:
        _debug_buffer.append((kwargs.get('split', ' ').join(str(i) for i in args), time.time()))
        if len(_debug_buffer) > _MAX_DEBUG_BUFFER:
            _debug_buffer.pop(0)
        if kwargs.get('flush', False):
            display()


def get_display_size() -> typing.Tuple:
    change_size()
    return _display_size

minimal_h, minimal_w = 30, 70

def change_size(h=None, w=None):
    global _size, _display_size
    if h is None or w is None:
        terminal_size = os.get_terminal_size()
        if h is None:
            h = int(terminal_size.lines)
        if w is None:
            w = int(terminal_size.columns)
    # if h < minimal_h or w < minimal_w:
    #     if h < minimal_h:
    #         h = minimal_h
    #     if w < minimal_w:
    #         w = minimal_w
    #     sys.stdout.write(f"\x1b[8;{h};{w}t")
    #     sys.stdout.flush()

    _display_size = (h, w)
    _size = (25, 60)

_old_size_buffer = None
def display_size_changed():
    global _old_size_buffer
    display_size = get_display_size()
    if _old_size_buffer != display_size:
        _old_size_buffer = display_size
        return True
    return False

def reset_dangerous_grids():
    dangerous_grids.clear()

def clear_snake():
    l_snake.clear()
    reset_dangerous_grids()

def push_snake(x, y):  # return False if (x, y) dangerous
    l_snake.append((x, y))
    if (x, y) in dangerous_grids:
        return False
    dangerous_grids.add((x, y))
    return True

def pop_snake():  # return popped element
    x, y = l_snake.pop(0)
    dangerous_grids.remove((x, y))
    return x, y

food_position = None

def generate_food():
    global food_position
    h, w = get_size()
    if len(dangerous_grids) < h * w * 4 // 5:
        while True:
            x, y = random.randint(0, h - 1), random.randint(0, w - 1)
            if not (x, y) in dangerous_grids:
                break
    else:
        safe_grids = []
        for x in range(h):
            for y in range(w):
                if (x, y) not in dangerous_grids:
                    safe_grids.append((x, y))
        if len(safe_grids) == 0:
            return None
        k = random.randint(0, len(safe_grids))
        x, y = k
    food_position = (x, y)
    debug(f'FOOD POSITION ({x}, {y})')
    return food_position

head_direction = (0, 1)
def set_head_direction(x, y):
    global head_direction
    head_direction = (x, y)

_direction_queue = []
def change_head_direction(x, y):
    global _direction_queue
    if len(_direction_queue):
        hd = _direction_queue[-1]
    else:
        hd = head_direction
    if x == -hd[0] and y == -hd[1]:
        return False
    if x == hd[0] and y == hd[1]:
        return False
    _direction_queue.append((x, y))
    return True

def apply_change_direction():
    if len(_direction_queue):
        x, y = _direction_queue.pop(0)
        set_head_direction(x, y)

score = 0
_highscore = None
def get_highscore():
    global _highscore
    if _highscore is None:
        try:
            with open("xw.dat", 'rb') as f:
                x = list(f.read(4))
                _highscore = ((x[3]*256+x[2])*256+x[1])*256+x[0]
        except FileNotFoundError:
            _highscore = 0
    return _highscore

def set_highscore(score, force=False):
    global _highscore
    if force or get_highscore() < score:
        _highscore = score
        p0 = score % 256
        p1 = score // 256 % 256
        p2 = score // (256 * 256) % 256
        p3 = score // (256 * 256 * 256)
        fbytes = bytes([p0, p1, p2, p3])
        with open("xw.dat", 'wb') as f:
            f.write(fbytes)
        return True
    return False

def set_score(new_score):
    global score
    score = new_score
    set_highscore(score)


def clear_highscore():
    set_highscore(0, True)

def init_game_data():
    h, w = get_size()
    clear_snake()
    push_snake(h // 2, w // 2 - 2)
    push_snake(h // 2, w // 2 - 1)
    push_snake(h // 2, w // 2 + 0)
    push_snake(h // 2, w // 2 + 1)
    set_head_direction(0, 1)
    generate_food()
    set_score(0)

def move():  # return false if pumped into barrier
    x, y = l_snake[-1]
    h, w = get_size()
    apply_change_direction()
    new_x, new_y = (x + head_direction[0]) % h, (y + head_direction[1]) % w
    if (new_x, new_y) == food_position:  # cannot pump into barrier
        set_score(score + 1)
        push_snake(new_x, new_y)
        generate_food()
        return True
    else:
        pop_snake()
        return push_snake(new_x, new_y)

UNSTARTED, PREPARING, PLAYING, PAUSED, KILLED, END, QUIT = 0, 6, 1, 2, 3, 4, 5
game_status = UNSTARTED

_old_display_dict = {}
def show_message(display, message, position='mid', align=None):
    h, w = get_display_size()
    # positions = position.split('-')
    lines = message.split('\n')
    hh = len(lines)
    if isinstance(position, str):
        if position == 'mid':
            if align is None:
                align = 'mid'
            h0 = (h-hh) // 2
            w0 = w // 2
        elif position == 'top-right':
            if align is None:
                align = 'right'
            h0 = 0
            w0 = w
        elif position == 'bottom-left':
            if align is None:
                align = 'left'
            h0 = h - hh
            w0 = 0
        else:
            raise NotImplementedError("Unsupported message position!")
        for i, line in enumerate(lines):
            ll = len(line)
            for j, x in enumerate(line):
                if align == 'mid':
                    w1 = (w - ll) // 2
                elif align == 'right':
                    w1 = w0 - ll
                else:
                    w1 = w0
                display[(h0 + i, w1 + j)] = x

def show_grid(display, grids=None, position='mid'):
    h, w = get_size()
    h0, w0 = get_display_size()
    dh, dw = (h0 - h) // 2, (w0 - w) // 2
    for (x, y), v in grids.items():
        display[(x + dh, y + dw)] = v

def cls_str():
    return '\033[2J'
def clear_screen(display):
    display[(-1, -1)] = (cls_str(), )

def has_cls(display):
    return display.get((-1, -1), None) == (cls_str(), )

def draw_frame(display):
    h, w = get_size()
    h0, w0 = get_display_size()
    dh, dw = (h0 - h) // 2, (w0 - w) // 2
    for i in range(dh, dh + h):
        display[(i, dw - 1)] = display[(i, dw + w)] = '|'
    for i in range(dw, dw + w):
        display[(dh - 1, i)] = display[(dh + h, i)] = '-'
    display[(dh - 1, dw - 1)] = display[(dh + h, dw - 1)] = display[(dh - 1, dw + w)] = display[(dh + h, dw + w)] = '+'

def get_new_display(game_status):
    new_display = {}
    if display_size_changed():
        clear_screen(new_display)
    if game_status == UNSTARTED:
        welcome_message = 'WELCOME TO GLUTTONOUS SNAKE!\n\nPRESS s TO START GAME.\n\n w - UP   \n a - LEFT \n s - ' \
                          'DOWN \n d - RIGHT\n\nPRESS q TO QUIT. '
        show_message(new_display, welcome_message)
    elif game_status == PLAYING:
        show_message(new_display, f'SCORE  {score:5d}\nHIGH  {get_highscore():5d}', 'top-right')
        show_grid(new_display, {i: '#' for i in dangerous_grids})
        if len(l_snake):
            show_grid(new_display, {l_snake[-1]: '@'})
        if food_position is not None:
            show_grid(new_display, {food_position: '$'})
    elif game_status == PAUSED:
        show_message(new_display, '\n\n\nGLUTTONOUS SNAKE\n\nPAUSED\n\nPRESS p TO RESUME.\nPRESS q TO QUIT.\n\n\n\n'
                                  ' w - UP   \n a - LEFT \n s - '
                                  'DOWN \n d - RIGHT')
    elif game_status == KILLED:
        show_message(new_display, f'SCORE  {score:5d}\nHIGH  {get_highscore():5d}', 'top-right')
        show_grid(new_display, {i: '#' for i in dangerous_grids})
        show_grid(new_display, {l_snake[-1]: ansi.AnsiColor(color8='red').wrap(b'\xf0\x9f\x98\x85'.decode('utf-8'))})
        if food_position is not None:
            show_grid(new_display, {food_position: '$'})
    elif game_status == END:
        show_message(new_display, f'GAME OVER.\nYOUR SCORE: {score:5d}\nHIGH SCORE: {get_highscore():5d}\nPRESS s TO RESTART.')
    elif game_status == QUIT:
        show_message(new_display, "ARE YOU SURE TO QUIT THE GAME?\ny      n")
    draw_frame(new_display)
    return new_display

def show_debug(display):
    global _debug, _debug_buffer
    if _debug and _debug_buffer:
        show_message(display, '\n'.join(i for i, _ in _debug_buffer), 'bottom-left')

def display(cls=False):
    global _old_display_dict
    new_display = get_new_display(game_status)
    if cls:
        clear_screen(new_display)
    show_debug(new_display)
    h, w = get_display_size()
    different_grids = {}
    if has_cls(new_display):
        _old_display_dict.clear()
        sys.stdout.write(cls_str())
    for k, v in new_display.items():
        if isinstance(v, str) and (k not in _old_display_dict or _old_display_dict[k] != v) and h > k[0] >= 0 and w > k[1] >= 0:
            different_grids[k] = v
        elif isinstance(v, tuple) and (h > k[0] >= 0 and w > k[1] >= 0):
            different_grids[k] = v[0]
    for k, v in _old_display_dict.items():
        if k not in new_display:
            different_grids[k] = '\x1b[m '  # restore this grid!
    # display
    contents = [(i, j, v) for (i, j), v in different_grids.items()]
    contents.sort()
    lx, ly = -100, -100
    continuous_parts = ''
    display_buf = ''
    # cls
    for i, (x, y, v) in enumerate(contents):
        flag = False
        if lx == x and ly == y - 1:
            # continuous
            continuous_parts += v
            flag = True
        else:
            display_buf += (continuous_parts) + (f'\033[{x+1};{y+1}H')
            continuous_parts = v
        if i == len(contents) - 1:
            display_buf += (continuous_parts)

        lx, ly = x, y
    _old_display_dict = new_display
    if contents:
        sys.stdout.write(display_buf)
        # debug("Display len:", len(display_buf), "Contents:", len(contents))
        # with open('e.json', 'a') as f:
        #     json.dump(contents, f)
        sys.stdout.flush()
        # time.sleep(1)


def change_game_status(new_status):
    global game_status
    game_status = new_status
    display()

_time = 0
def update_time():
    global _time
    _time = time.time()
def restore_game():
    global game_status
    change_game_status(PLAYING)
    update_time()

def pause_game():
    global game_status
    change_game_status(PAUSED)
    update_time()

def pause_restore():
    if game_status == PAUSED:
        restore_game()
    elif game_status == PLAYING:
        pause_game()
    return game_status

_timer_limit = 0.1
_killed_time_limit = 2
def game_step():
    if game_status == PLAYING:
        if time.time() - _time >= _timer_limit:
            x = move()
            if not x:
                change_game_status(KILLED)
            display()
            update_time()
        return
    if game_status == KILLED:
        if time.time() - _time >= _killed_time_limit:
            change_game_status(END)
            display()
        return
    display()



def loop_on(function, *args, end_condition=None, **kwargs):
    while True:
        rv = function(*args, **kwargs)
        if callable(end_condition) and end_condition(rv):
            return rv

def quit_game():
    global game_status
    old = game_status
    change_game_status(QUIT)
    nb.set_endkeys(['y', '\n'])
    display()
    answer = loop_on(get_input, check_answer, end_condition=lambda x: x in {True, False})
    if answer:
        print('\033[2J')
        exit(0)
    nb.set_endkeys([])
    change_game_status(old)
    display()

def start_game():
    change_game_status(PREPARING)
    display()
    init_game_data()
    restore_game()
    display()

def check_answer(ch):
    if ch == 'y':
        return True
    elif ch == 'n':
        return False
    return None

def check_playing_command(ch):
    if ch == 's':
        return change_head_direction(1, 0)
    elif ch == 'a':
        return change_head_direction(0, -1)
    elif ch == 'w':
        return change_head_direction(-1, 0)
    elif ch == 'd':
        return change_head_direction(0, 1)
    elif ch == 'p':
        return pause_restore()
    elif ch == 'q':
        return quit_game()
    return None

def check_paused_command(ch):
    if ch == 'p':
        return pause_restore()
    elif ch == 'q':
        return quit_game()
    return None

def check_unstarted_command(ch):
    if ch == 's':
        return start_game()
    elif ch == 'q':
        return quit_game()
    return None

def check(ch):
    if game_status == UNSTARTED:
        return check_unstarted_command(ch)
    elif game_status == PREPARING:
        return None
    elif game_status == PLAYING:
        return check_playing_command(ch)
    elif game_status == PAUSED:
        return check_paused_command(ch)
    elif game_status == END:
        return check_unstarted_command(ch)
    elif game_status == QUIT:
        return check_answer(ch)
    return None


def get_input(check_function):
    if nb.kbhit():
        ch = nb.getch()
        debug('GOT ', ch, flush=True)
        return check_function(ch)
    return None


def main_loop_function():
    get_input(check)
    game_step()

if __name__ == '__main__':
    print('\033[?25l')
    display(cls=True)
    loop_on(main_loop_function)

def exitfunction():
    nbclose()
    print("\033[?25h")
    exit(0)