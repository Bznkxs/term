import traceback

import cv2
import os, sys
import numpy as np
from ansi import AnsiColor
from matplotlib import pyplot as plt
from non_blocking_input import nbprepare, nbclose

import threading
import time
from config_prev import dezek

bw = 2

finished = True
input_char = ''

mode = 'rgb'

colors = {}


def getcolor(r, g, b):
    if (r, g, b) not in colors:
        colors[(r, g, b)] = AnsiColor(r=r, g=g, b=b)
    colors[(r, g, b)].set_mode(mode)
    return colors[(r, g, b)]


# print(getcolor(255,0,0).square())
def col_array(start, cols):
    wt = ' ' * (bw - 1)
    ret = []
    if cols > 1000:
        ret.append('   ' + (' ' * (999 * bw)).join(f'{wt}{i // 1000:d}' for i in range(start, cols, 1000)))
    if cols > 100:
        ret.append('   ' + (' ' * (99 * bw)).join(f'{wt}{i // 100 % 10:d}' for i in range(start, cols, 100)))
    ret.append('   ' + (' ' * (9 * bw)).join(f'{wt}{i // 10 % 10:d}' for i in range(start, cols, 10)))
    ret.append('   ' + ''.join(f'{wt}{i % 10:d}' for i in range(start, cols)))
    return '\n'.join(ret)


# def show(img: np.ndarray, t, l):
stop = False
running_display = None


def write(stt, file):
    buf_len = 1 << 16
    for i in range(0, len(stt), buf_len):
        if stop:
            print('\033[m', file=file)
            return
        if not file:
            sys.stdout.write(stt[i: i + buf_len])
        else:
            print(stt[i: i + buf_len], end='', file=file)
    if not file:
        if stop:
            return
        sys.stdout.write('\n')
        sys.stdout.flush()
    else:
        if stop:
            return
        print(file=file, flush=True)


def show(img: np.ndarray, t, l, fd=None):
    if fd is None:
        fd = sys.stdout
    h, w, _ = img.shape
    wt = ' ' * (bw)
    rows = []
    for i in range(h):
        row = [f'{i + t:3d}']
        acc = 0
        for j in range(w):
            if stop:
                return
            r, g, b = img[i, j]
            if j < w - 1 and (img[i, j] == img[i, j + 1]).all():
                acc += 1
            else:
                dd = getcolor(r, g, b).wrap(wt * (acc + 1), reset=False)  # \#getcolor(r,g,b)
                # fprint(dd,r,g,b,wt,acc+1)
                acc = 0
                row.append(dd)

        row.append(AnsiColor.reset)
        rows.append(''.join(row))
    imgstr = '\n'.join(rows)
    print('\033[2J', file=fd)  # clear screen
    print('\033[H', file=fd)  # move to top left of screen CSI n ; m H
    # print('\033[2J')  # clear screen
    if stop:
        return
    print(col_array(l, l + w), file=fd)
    write(imgstr, file=fd)


def display(img2, frame_t, frame_l, fd=None, hint=None):
    show(img2, frame_t, frame_l, fd)
    if hint:
        print(hint, end='\r')


def adjust(img, frame_t, frame_h, frame_l, frame_w, pooling_factor, pooling_type, fd=None, hint=None):
    h, w, _ = img.shape
    h1, w1 = (h + pooling_factor - 1) // pooling_factor, (w + pooling_factor - 1) // pooling_factor
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

    return h1, w1


def do_exit(exit_code=0):
    nbclose()
    exit(exit_code)


if __name__ == '__main__':
    nbi = nbprepare()
    nbi.set_endkey('q')
    pooling_factor = 1
    try:
        if len(sys.argv) > 1:
            img = cv2.imread(sys.argv[1])
        else:
            img = dezek()
            pooling_factor = 6

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    except Exception:
        img = np.zeros([1, 1, 3])
    if len(sys.argv) == 3:
        mode = sys.argv[2]

    terminal_size = os.get_terminal_size()
    fixed_size = None
    old_fh, old_fw = frame_h, frame_w = int(terminal_size.lines - 5), int(terminal_size.columns // 2 - 5)
    frame_l = frame_t = 0
    pooling_type = 'nearest'
    h, w, _ = img.shape
    h_c, w_c = adjust(img, frame_t, frame_h, frame_l, frame_w, pooling_factor, pooling_type)
    # exit(0)
    xxx = 0

    op_number = 1
    number_stat = 0
    change = 0
    try:
        while True:
            change = 0
            if nbi.khbit():
                p = nbi.getch()
                # print(f"[main] catch {p}")
            else:
                continue
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
                    do_exit(0)
                elif p == 'l':
                    epath = nbi.input('l')
                    ee = cv2.imread(epath)
                    if ee is not None:
                        img = cv2.cvtColor(ee, cv2.COLOR_BGR2RGB)
                        pooling_factor = 1
                        frame_l = frame_t = 0
                        h, w, _ = img.shape
                        change = 1
                elif p == 'b':
                    if bw == 2:
                        bw = 3
                    elif bw == 3:
                        bw = 2
                    change = 1
                elif p == 'x':
                    nh = int(nbi.input('h'))
                    nw = int(nbi.input('w'))
                    fixed_size = nh, nw
                    change = 1
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
                    change = 1
                old_fh, old_fw = frame_h, frame_w
                opn, ns, p1 = op_number, number_stat, p
                _tmp = p1
                if ns:
                    _tmp = f'{opn}' + p1
                if change:
                    h_c, w_c = adjust(img, frame_t, frame_h, frame_l, frame_w, pooling_factor, pooling_type, cur_fd,
                                      _tmp)
                    change = 0

                op_number = 1
                number_stat = 0
    except Exception as _:
        print(_)
    finally:
        do_exit(0)
