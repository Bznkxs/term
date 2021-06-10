import sys
import select
import time
import tty

try:
    import msvcrt
except ImportError:
    import termios
import threading

xp = ''

_debug = False


def debug(*args, **kwargs):
    if _debug:
        print(*args, **kwargs)


def try_get_c():
    global xp
    xp = sys.stdin.read(1)


def original_practice():
    # https://stackoverflow.com/questions/2408560/non-blocking-console-input#2409034
    try:  # Windows
        import msvcrt

        num = 0
        done = False
        while not done:
            print(num)
            num += 1

            if msvcrt.kbhit():
                print("you pressed", msvcrt.getch(), "so now i will quit")
                done = True
    except ImportError:  # Unix
        import sys
        import select
        import tty
        import termios
        def isData():
            return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())

            i = 0
            buf = []
            while 1:
                i += 1
                global xp
                if xp:
                    c = xp
                    xp = ''
                    if c == '\x1b':  # x1b is ESC
                        break
                    if c == '\x7f':
                        buf = buf[:-1]
                    else:
                        buf.append(c)
                if isData():
                    tmp_buf = []
                    while True:
                        t0 = time.time()
                        tr = threading.Thread(target=try_get_c)
                        tr.daemon = True
                        tr.start()
                        flag = True
                        threshold = 0.01
                        while time.time() - t0 < threshold:
                            if not tr.is_alive():
                                tmp_buf.append(xp)
                                xp = ''
                                flag = False
                                break
                        if flag:
                            break

                    flag = False
                    for c in tmp_buf:
                        if c == '\x1b':  # x1b is ESC
                            flag = True
                            break
                        if c == '\x7f':
                            buf = buf[:-1]
                        else:
                            buf.append(c)
                    if flag:
                        break
                for _i in buf:
                    print(_i, end='')
                print()
                time.sleep(0.8)

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


class NonBlockingIO:
    def khbit(self) -> bool:
        raise NotImplementedError

    def getch(self) -> str:
        raise NotImplementedError

    def nonblock_read(self):
        if self.khbit():
            return self.getch()
        return None

    def close(self):  # should call explicitly
        pass

    def set_endkey(self, key):
        pass


class WindowsNonBlockingIO(NonBlockingIO):
    def __init__(self):
        import khbit

    def khbit(self):
        return msvcrt.khbit()

    def getch(self):
        return msvcrt.getch()


class UnixNonBlockingIO(NonBlockingIO):
    def __init__(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        self._xp = ''  # this belongs to the input_daemon thread. main thread must read it after getchar is finished.
        self._input_daemon = None  # the input daemon thread.
        self._str_buf = []  # string buffer
        self.timeout = 0.0001  # time for input timeout
        self.endkey = None
        self.enable_input = True
        self.disable_state = True
        self.closed = False

    def set_endkey(self, key):
        self.endkey = key

    def input(self, hint):
        print(hint, end=' ', flush=True)
        self.set_disable_state(False)
        l_in = []
        p = 0  # insert pointer
        st = 0  # status
        x = self.getch()
        old_len = 0
        old_p = 0
        while x != '\n':
            if x == '\x1b':
                st = 27
            elif x == '\x7f':
                st = 0
                if p > 0:
                    l_in.pop(p-1)
                    p -= 1
            elif st == 0:
                l_in.insert(p, x)
                p += 1
            elif st == 27:
                if x == '[':
                    st = 28
                else:
                    st = 0
            elif st == 28:
                if x == 'C':
                    if p < len(l_in):
                        p += 1
                elif x == 'D':
                    if p > 0:
                        p -= 1
                if x == '3':
                    st = 29
                elif x == '2':
                    st = 30
                else:
                    st = 0
            elif st == 29:
                if x == '~':
                    if p < len(l_in):
                        l_in.pop(p)
                st = 0
            elif st == 30:
                if x == '~':
                    st = 0
            # paint line
            debug(f"[input] {''.join(l_in)}")
            ansi_seq = ''
            if old_p > 0:
                ansi_seq += f'\x1b[{old_p}D'
            ansi_seq += ''.join(l_in)
            if old_len > len(l_in):
                ansi_seq += ' '*(old_len-len(l_in))
                if old_len-p > 0:
                    ansi_seq += f'\x1b[{old_len-p}D'
            elif len(l_in)-p>0:
                ansi_seq += f'\x1b[{len(l_in)-p}D'
            print(ansi_seq, end='', flush=True)
            if p < len(l_in):
                debug(f'\x1b[4m{l_in[p]}\x1b[m')
            else:
                debug(f'\x1b[4m \x1b[m')
            debug("##\x1b[0Da\x1b[0D@@")
            old_len = len(l_in)
            old_p = p
            x = self.getch()

        self.set_disable_state(True)
        l_in = ''.join(l_in)
        return l_in

    def set_disable_state(self, disable_state):
        self.disable_state = disable_state

    def _getchar(self):
        self._xp = sys.stdin.read(1)

    def _safe_collect(self):
        """
        read and clear _xp.
        :return: 2 if input daemon is alive; 0 if collected; 1 if not collected (_xp is empty)
        """
        if self._input_daemon is not None and self._input_daemon.is_alive():
            return 2
        self._input_daemon = None
        if self._xp:
            if self._xp == self.endkey and self.disable_state:
                self.enable_input = False
            debug(f"collected [ {self._xp} ]")
            self._str_buf.append(self._xp)
            self._xp = ''
            return 0
        return 1

    def _peek_buf(self):
        self._safe_collect()
        if len(self._str_buf):
            return self._str_buf[0]
        return None

    def _pop_buf(self):
        head = self._peek_buf()
        if head:
            self._str_buf.pop(0)
        return head

    # a very hard procedure to abstract to these two.
    def _data_ready(self):
        """
        This appears to be True only when the new input is ready and NONE OF THEM is read.
        For example:
        <phase 1>
        [INPUT] s
        [INPUT] a
        [INPUT] e
        [ASK]  data_ready?
        [ANSWER] yes
        [getchar] s
        [ASK]  data_ready?
        [ANSWER] NO
        [getchar] a  (but this is not safe!)

        <phase 2>
        [INPUT] c
        [INPUT] d
        [ASK] data_ready?
        [ANSWER] yes
        [getchar] e
        [ASK] data_ready?
        [ANSWER] yes
        [getchar] c
        [ASK] data_ready?
        [ANSWER] NO
        :return:
        """
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

    def _new_thread(self):
        if self.enable_input:
            self._input_daemon = threading.Thread(target=self._getchar)
            debug("[new] new daemon.")
            self._input_daemon.daemon = True
            self._input_daemon.start()
            return True
        return False

    def _try_read(self):
        """
        :return: True if there
        """
        if self._safe_collect() != 2:
            if not self._new_thread():
                return False
        t0 = time.time()
        while time.time() - t0 < self.timeout:
            if self._safe_collect() != 2:
                return True
        return False

    def khbit(self):

        if self._peek_buf():
            debug("[khbit] T1")
            return True
        data_ready = self._data_ready()
        if data_ready:
            debug("[khbit] T2")
            return True
        x = self._try_read()
        if x:
            debug("[khbit] T3")
        return x

    def getch(self):
        px = self._pop_buf()
        if px:
            debug(f"[getch] 1] {px}")
            return px

        while self._try_read():
            continue
        px = self._pop_buf()
        if px:
            debug(f"[getch] 2] {px}")
            return px
        else:
            debug(f"[getch] 3] stuck")
            while self._safe_collect() != 0:
                continue

            return self._pop_buf()

    def close(self):
        if self.closed:
            return
        debug(f"[Unix close] daemon status: {self._safe_collect()}")
        self.closed = True
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)


_io_obj = None


def nbprepare():
    global _io_obj
    try:
        _io_obj = WindowsNonBlockingIO()
    except Exception as _:
        try:
            _io_obj = UnixNonBlockingIO()
        except Exception as __:
            print(__)
            _io_obj = None
    return _io_obj


def nbclose():
    # must call explicitly
    debug("[nbclose]")
    global _io_obj
    if isinstance(_io_obj, NonBlockingIO):
        try:
            _io_obj.close()
            return True
        except Exception as _:
            print(_)
            return False
    return False


if __name__ == '__main__':
    original_practice()
