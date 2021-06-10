import traceback

import cv2
import imageio
import os, sys
import numpy as np
from ansi import AnsiColor
from matplotlib import pyplot as plt
from non_blocking_input import nbprepare, nbclose
import atexit
import threading
import time
from config_prev import dezek

bw = 2

finished = True
input_char = ''

mode = 'rgb'

colors = {}

def cls(fd=None):
    restore_screen_buf()
    print('\033[2J', file=fd)

def getcolor(r, g, b):
    if (r, g, b) not in colors:
        colors[(r, g, b)] = AnsiColor(r=r, g=g, b=b)
    colors[(r, g, b)].set_mode(mode)
    return colors[(r, g, b)]


# print(getcolor(255,0,0).square())

prespace = '   '
def col_array(start, cols, mw):
    wt = ' ' * (bw - 1)
    ret = []
    def makeup(s):
        ls = len(s)
        if ls < mw:
            m = ' ' * (mw - ls)
        else:
            m = ''
        return s + m

    if cols > 1000:
        ret.append(makeup(prespace + (' ' * (999 * bw)).join(f'{wt}{i // 1000:d}' for i in range(start, cols, 1000))))
    if cols > 100:
        ret.append(makeup(prespace + (' ' * (99 * bw)).join(f'{wt}{i // 100 % 10:d}' for i in range(start, cols, 100))))
    ret.append(makeup(prespace + (' ' * (9 * bw)).join(f'{wt}{i // 10 % 10:d}' for i in range(start, cols, 10))))
    ret.append(makeup(prespace + ''.join(f'{wt}{i % 10:d}' for i in range(start, cols))))
    return '\n'.join(ret)


# def show(img: np.ndarray, t, l):
stop = False
running_display = None


def write(stt, file):
    buf_len = 1 << 16
    for i in range(0, len(stt), buf_len):
        if stop and file == sys.stdout:
            print('\033[m', file=file)
            return
        if not file:
            sys.stdout.write(stt[i: i + buf_len])
        else:
            print(stt[i: i + buf_len], end='', file=file)
    if not file:
        if stop and file == sys.stdout:
            return
        sys.stdout.write('\n')
        sys.stdout.flush()
    else:
        if stop and file == sys.stdout:
            return
        print(file=file, flush=True)

screen_buf = np.ones([1,1,3]) * (-100)
_show_oldh, _show_oldw = 1, 1
old_b = 2
def restore_screen_buf():
    global screen_buf
    screen_buf = np.ones([_show_oldh,_show_oldw // old_b,3]) * (-100)
open_buf_strategy = False
def show(img: np.ndarray, t, l, fd=None):
    global _show_oldw, _show_oldh, screen_buf, old_b
    terminal_size = os.get_terminal_size()
    mh, mw = int(terminal_size.lines), int(terminal_size.columns)
    mh = min(mh, _show_oldh)
    mw = min(mw, _show_oldw)

    if fd is None:
        fd = sys.stdout
    # if fd != sys.stdout:
    #     cls(fd)
    h, w, _ = img.shape
    if old_b != bw:
        restore_screen_buf()

    h0, w0, _ = screen_buf.shape

    if h0 >= h and w0 >= w:
        screen_buf = screen_buf[:h, :w]
    elif h0 >= h and w0 < w:
        screen_buf = screen_buf[:h]
        screen_buf = np.hstack([screen_buf, np.ones([h, w - w0, 3], dtype=int) * (-100)])
    elif h0 < h and w0 >= w:
        screen_buf = screen_buf[:, :w]
        screen_buf = np.vstack([screen_buf, np.ones([h - h0, w, 3], dtype=int) * (-100)])
    else:
        _1 = np.ones([h, w, 3], dtype=int) * (-100)
        _1[:h0, :w0] = screen_buf
        screen_buf = _1
    wt = ' ' * (bw)
    rows = []
    threshold = 0
    judge_buf = ((screen_buf - img) ** 2).sum(axis=2) > threshold  # those that need to change
    screen_buf[judge_buf] = img[judge_buf]
    for i in range(h):
        row = [f'{i + t:3d}']
        acc_same = 0
        acc_buf = 0
        buf_strategy = False
        for j in range(w):
            if stop and fd == sys.stdout:
                restore_screen_buf()
                return
            r, g, b = img[i, j]
            if acc_buf >= acc_same:
                buf_strategy = open_buf_strategy
            else:
                buf_strategy = False
            # same as buffer
            if buf_strategy:
                if not judge_buf[i, j]:
                    acc_buf += 1
                else:
                    if acc_buf:
                        row.append(f'\x1b[{acc_buf * bw}C')
                    # row.append(getcolor(r, g, b).wrap(wt, reset=False))
                    buf_strategy = False
                    acc_buf = 0
            if not buf_strategy:
                row.append(getcolor(r, g, b).wrap(wt * (acc_same + 1), reset=False))
                if j < w - 1 and (img[i, j] == img[i, j + 1]).all():
                    acc_same += 1
                else:
                    dd = getcolor(r, g, b).wrap(wt * (acc_same + 1), reset=False)  # \#getcolor(r,g,b)
                    # fprint(dd,r,g,b,wt,acc+1)
                    acc_same = 0
                    row.append(dd)
        row.append(AnsiColor.reset)
        if w * bw + len(prespace) < mw:
            if acc_buf:
                row.append(f'\x1b[{acc_buf * bw}C')
            row.append(' ' * (mw - w * bw - len(prespace)))
        rows.append(''.join(row))
    if h < mh - len(prespace):
        rows += [' ' * mw] * (mh - len(prespace) - h)
    imgstr = '\n'.join(rows)
    # if _show_oldh > h or _show_oldw > w:
    #     print('\033[2J', file=fd)  # clear screen

    print('\033[H', file=fd)  # move to top left of screen CSI n ; m H
    # print('\033[2J')  # clear screen
    if stop and fd == sys.stdout:
        restore_screen_buf()
        return
    print(col_array(l, l + w, mw), file=fd)
    write(imgstr, file=fd)
    if stop and fd == sys.stdout:
        restore_screen_buf()
        return
    _show_oldh, _show_oldw = h + len(prespace), w * bw + len(prespace)
    old_b = bw

def give_hint(hint=None):
    return
    if hint:
        print(hint, end='\r')

def display(img2, frame_t, frame_l, fd=None, hint=None):
    try:
        show(img2, frame_t, frame_l, fd)
        give_hint(hint)
    except Exception:
        pass


def adjust(img, frame_t, frame_h, frame_l, frame_w, pooling_factor, pooling_type, fd=None, hint=None, change=1):
    h, w, _ = getshape(img)
    h1, w1 = (h + pooling_factor - 1) // pooling_factor, (w + pooling_factor - 1) // pooling_factor
    if frame_t > h1:
        frame_t = h1
    if frame_l > w1:
        frame_l = w1
    if change:
        img1 = np.zeros([h1 * pooling_factor, w1 * pooling_factor, 3], dtype=int)
        img1[:h, :w] = img
        img2 = np.zeros([h1, w1, 3], dtype=int)
        if pooling_type == 'mean':
            for i in range(pooling_factor):
                for j in range(pooling_factor):
                    img2 += img1[i::pooling_factor, j::pooling_factor]
            img2 //= pooling_factor ** 2
        elif pooling_type == 'nearest':
            img2 = img1[::pooling_factor, ::pooling_factor]
        img2 = img2[frame_t:frame_t + frame_h, frame_l:frame_l + frame_w]

        # print(frame_w, frame_h)
        def _local_():
            display(img2, frame_t, frame_l, fd, hint)

        global running_display, stop
        if running_display:
            stop = True
            while running_display.is_alive():
                continue
        stop = False
        running_display = threading.Thread(target=_local_)
        running_display.daemon = True
        running_display.start()
    else:
        give_hint(hint)
    return h1, w1, frame_t, frame_l




def read_image(target_file):
    try:
        im = imageio.get_reader(target_file)
    except Exception:
        try:
            im = imageio.imread(target_file)
        except Exception:
            return None
    initframe()
    cls()
    return im

from imageio.core.format import Format

def is_reader(im):
    if isinstance(im, Format.Reader):
        return True
    return False

def getshape(im):
    if is_reader(im):
        return im.get_data(0).shape
    return im.shape

current_frame = 0
current_frame_buffer = None
_new_img_mark = False

def initframe():
    global current_frame_buffer, current_frame, _new_img_mark
    current_frame = -1
    current_frame_buffer = None
    _new_img_mark = True


def read_new_img_mark():
    global _new_img_mark
    if _new_img_mark:
        _new_img_mark = False
        return True
    return False

def _inner_next_frame(im):  # one image for one generator
    global current_frame_buffer, current_frame
    while True:
        for i, x in enumerate(im):
            current_frame_buffer = x
            current_frame = i
            yield i

next_frame_getter = None
def nextframe(im):
    global next_frame_getter
    if read_new_img_mark():  # at new image
        next_frame_getter = None  # remove old getter
    if is_reader(im): # should have getter
        if next_frame_getter is None:
            next_frame_getter = _inner_next_frame(im)  # get new getter
        return next(next_frame_getter)
    return 0  # single image


def frame(im, background=(255,255,255)):
    global current_frame_buffer
    if is_reader(im):
        if current_frame_buffer is None:
            nextframe(im)  # load frame
        im = current_frame_buffer
    _, __, channels = getshape(im)
    # print("SSS", _, __, channels)
    if channels == 4:
        # blend with background
        a = im[:, :, 3]
        for i in range(3):
            x, y = background[i], im[:, :, i]
            # b, a = a, b
            im[:, :, i] = (x - y) * a // 255 + y
        im = im[:, :, :3]
    im[current_frame // 10, current_frame % 10] = 30
    return im

def num_frames(im):
    if is_reader(im):
        w = im.get_length()
        if np.isinf(w):
            return -1
        return w
    return 1

if __name__ == '__main__':

    nbi = nbprepare()
    atexit.register(nbclose)
    nbi.set_endkey('q')
    pooling_factor = 1
    try:
        if len(sys.argv) > 1:
            img = read_image(sys.argv[1])
        else:
            img = dezek()
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pooling_factor = 6

    except Exception:
        img = np.zeros([1, 1, 3])
    if len(sys.argv) == 3:
        mode = sys.argv[2]

    terminal_size = os.get_terminal_size()
    fixed_size = None
    old_fh, old_fw = frame_h, frame_w = int(terminal_size.lines - 5), int(terminal_size.columns // 2 - 5)
    frame_l = frame_t = 0
    pooling_type = 'nearest'
    h, w, _ = getshape(img)
    h_c, w_c, frame_t, frame_l = adjust(frame(img), frame_t, frame_h, frame_l, frame_w, pooling_factor, pooling_type)

    xxx = 0

    op_number = 1
    number_stat = 0
    change = 0

    old_frame_p = 0
    frame_time_start = time.time()
    frame_time = frame_time_start
    frame_time_limit = 1 / 24
    frame_p = None
    special = ''
    modtime = None  # unknown
    autoplay = True
    try:
        while True:
            change = 0
            if nbi.kbhit():
                p = nbi.getch()
            else:
                p = ''
            # calcfp = int((time.time() - frame_time_start) / frame_time_limit)
            # if modtime:
            #     calcfp %= modtime
            # while calcfp != frame_p:
            #     ofrp = frame_p
            #     frame_p = nextframe(img)
            #     if ofrp is not None and frame_p == 0:
            #         modtime = ofrp + 1
            #         calcfp %= modtime
            if autoplay:
                if time.time() - frame_time > frame_time_limit:
                    frame_p = nextframe(img)
                    frame_time = time.time()
                if frame_p != old_frame_p:
                    change = 1
                old_frame_p = frame_p
            if p.isnumeric():
                x = int(p)
                number_stat = number_stat * 10 + x
                op_number = number_stat
                print(op_number, end='\r')
            else:
                cur_fd = None
                if p == 'j':
                    if pooling_factor > op_number:
                        pooling_factor -= op_number
                        change = 1
                elif p == 'k':
                    if pooling_factor <= max(h, w) - op_number:
                        pooling_factor += op_number
                        change = 1
                elif p == 'w':
                    if frame_t >= op_number:
                        frame_t -= op_number
                        change = 1
                elif p == 's':
                    if frame_t <= h_c - op_number:
                        frame_t += op_number
                        change = 1
                elif p == 'a':
                    if frame_l >= op_number:
                        frame_l -= op_number
                        change = 1
                elif p == 'd':
                    if frame_l <= w_c - op_number:
                        frame_l += op_number
                        change = 1
                elif p == 'q':
                    exit(0)
                elif p == 'l':
                    epath = nbi.input('l')
                    ee = read_image(epath)
                    if ee is not None:
                        img = ee
                        pooling_factor = 1
                        frame_l = frame_t = 0
                        h, w, _ = getshape(img)
                        old_frame_p = 0
                        frame_time_start = time.time()
                        frame_time_limit = 1 / 24
                        frame_p = None
                        special = ''
                        modtime = None  # unknown
                        change = 1
                    else:
                        special = f'l {epath}: failed.'
                elif p == 'b':
                    if bw == 2:
                        bw = 3
                    elif bw == 3:
                        bw = 2
                    change = 1
                elif p == 'x':
                    try:
                        nh = int(nbi.input('h'))
                        nw = int(nbi.input('w'))
                        fixed_size = nh, nw
                        change = 1
                    except Exception:
                        change = 0

                elif p == 'f':
                    fixed_size = None
                    change = 1
                elif p == 'p':
                    if pooling_type == 'mean':
                        pooling_type = 'nearest'
                    elif pooling_type == 'nearest':
                        pooling_type = 'mean'
                    change = 1
                elif p == 'm':
                    if mode == 'rgb':
                        mode = 'color256'
                    elif mode == 'color256':
                        mode = 'color8'
                    elif mode == 'color8':
                        mode = 'grey'
                    elif mode == 'grey':
                        mode = 'rgb'
                    change = 1
                elif p == 't':
                    epath = nbi.input("t")
                    try:
                        cur_fd = open(epath, 'w')
                    except Exception:
                        cur_fd = None
                    change=1
                elif p == 'o':
                    open_buf_strategy = not open_buf_strategy
                elif p == 'r':
                    cls()
                elif p == 'P':
                    autoplay = not autoplay
                    frame_time = frame_time_start = time.time()
                elif p == 'n':
                    if not autoplay:
                        frame_p = nextframe(img)
                        change = 1
                terminal_size = os.get_terminal_size()
                if fixed_size is None:
                    frame_h, frame_w = int(terminal_size.lines - 5), int(terminal_size.columns // bw - 5)
                else:
                    frame_h, frame_w = fixed_size
                    if frame_h == -1:
                        frame_h = int(terminal_size.lines - 5)
                    if frame_w == -1:
                        frame_w = int(terminal_size.columns // bw - 5)
                if old_fh != frame_h or old_fw != frame_w:
                    cls()
                    change = 1
                old_fh, old_fw = frame_h, frame_w
                opn, ns, p1 = op_number, number_stat, p
                _tmp = p1
                if ns:
                    _tmp = f'{opn}' + p1
                if special:
                    _tmp = special
                    special = ''

                h_c, w_c, frame_t, frame_l = adjust(frame(img), frame_t, frame_h, frame_l, frame_w, pooling_factor, pooling_type, cur_fd,
                                                    _tmp, change)
                change = 0

                op_number = 1
                number_stat = 0
    except Exception as _:
        while running_display:
            stop = True
            continue
        print('\x1b[m')
        traceback.print_exc(file='traceback')

