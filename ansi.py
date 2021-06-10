

def print_col():
    for i in range(256):
        print(i // 100, end='')
    print()
    for i in range(256):
        print(i // 10 % 10, end='')
    print()
    for i in range(256):
        print(i % 10, end='')
    print()


std_color_dict = {
    'black': 0,
    'red': 1,
    'green': 2,
    'yellow': 3,
    'blue': 4,
    'magneta': 5,
    'cyan': 6,
    'white': 7,
    'default': 9,
    'bright black': 60,
    'bright red': 61,
    'bright green': 62,
    'bright yellow': 63,
    'bright blue': 64,
    'bright magneta': 65,
    'bright cyan': 66,
    'bright white': 67,
}


def color8(color):
    if isinstance(color, str):
        return std_color_dict[color.lower()]
    return color


def color8_to_color256(color8):
    if color8 < 60:
        return color8
    return color8 - 52


def level(c, n_scale, full=255):
    # n_scale: number of ranges
    # n_scale + 1 values
    # 0, ..., n_scale
    return int(c * n_scale / full + 0.5)


def scale(l, n_scale, full=255):
    return l * full / n_scale


def rgb_to_ansi_256(r, g, b):
    if r == g and g == b:  # greyscale
        greyscale = level(r, 25)
        if greyscale == 0:
            return 16  # black
        elif greyscale == 25:
            return 231  # white
        else:
            return 231 + greyscale
    else:
        # 16 + 36 * r + 6 * g + b = color
        r_scale = level(r, 5)
        g_scale = level(g, 5)
        b_scale = level(b, 5)
        color = 16 + 36 * r_scale + 6 * g_scale + b_scale
        return color


std_color_map = {
    "ubuntu": [(1, 1, 1), (222, 56, 43), (57, 181, 74), (255, 199, 6),
               (0, 111, 184), (118, 38, 113), (44, 181, 233), (204, 204, 204),
               (128, 128, 128), (255, 0, 0), (0, 255, 0), (255, 255, 0),
               (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)],
}


def ansi_256_to_rgb(color256):
    # follow ubuntu
    if color256 < 16:
        return std_color_map['ubuntu'][color256]
    elif color256 < 232:
        cl = color256 - 16
        r = scale(cl // 36, 5)
        g = scale(cl % 36 // 6, 5)
        b = scale(cl % 6, 5)
        return r, g, b
    r = g = b = int((color256 - 232) * 247 / 24 + 8 + 0.5)
    return r, g, b


def color8_to_rgb(color):
    return ansi_256_to_rgb(color8_to_color256(color))

def rgb_to_color8(r, g, b):
    mv = 1e10
    mi = 0
    for cl in range(16):
        r0, g0, b0 = std_color_map['ubuntu'][cl]
        dist = (r0-r)**2+(g0-g)**2+(b0-b)**2
        if dist < mv:
            mv = dist
            mi = cl
    return color256_to_color8(mi)

def color256_to_color8(color):
    if color < 8:
        return color
    if color < 16:
        return color + 52
    return rgb_to_color8(*ansi_256_to_rgb(color))

# helper function of the conversions above
def convert(mode_from, mode_to, value_in):
    if mode_from == mode_to:
        return value_in
    if mode_to == 'color256':
        if mode_from == 'rgb':
            return rgb_to_ansi_256(*value_in)
        else:
            return color8_to_color256(value_in)
    elif mode_to == 'rgb':
        if mode_from == 'color256':
            return ansi_256_to_rgb(value_in)
        else:
            return color8_to_rgb(value_in)
    elif mode_to == 'color8':
        if mode_from == 'color256':
            return color256_to_color8(value_in)
        else:
            return rgb_to_color8(*value_in)


class AnsiColor:
    reset = '\033[m'

    def try_set_mode(self, mode):
        if self.mode is None:
            self.mode = mode

    def set_mode(self, mode):
        self.mode = mode

    def read_mode(self, ansi):
        self.mode = 'rgb'  # return 'rgb', 'color256' or 'color8'

    def __init__(self, **kwargs):
        """
        :argument ansi: ansi string
        :argument r: red scale (0 ~ 255)
        :argument g: green scale (0 ~ 255)
        :argument b: blue scale (0 ~ 255)
        :argument color256: 256-bit color
        :argument color8: 8-bit color
        :argument mode: color mode
        :argument foreground: False, foreground
        """
        self.foreground = kwargs.get('foreground', False)
        if 'mode' in kwargs:
            self.mode = kwargs['mode']
        else:
            self.mode = None
        if 'ansi' in kwargs:
            self.raw_ansi = kwargs['ansi']
            self.read_mode(self.raw_ansi)
        elif 'r' in kwargs and 'g' in kwargs and 'b' in kwargs:
            self.rgb = (kwargs['r'], kwargs['g'], kwargs['b'])
            self.try_set_mode('rgb')
        elif 'color256' in kwargs:
            self.color256 = kwargs['color256']
            self.try_set_mode('color256')
        elif 'color8' in kwargs:
            self.color8 = color8(kwargs['color8'])
            self.try_set_mode('color8')
        else:
            raise ValueError("Unsupported color format.")
        self.update_value()
        self.cache = {}

    def update_value(self):
        """
        Unify format.
        """
        for source_mode in ['rgb', 'color256', 'color8']:
            if hasattr(self, source_mode):
                for target_mode in ['rgb', 'color256', 'color8']:
                    setattr(self, target_mode, convert(source_mode, target_mode, getattr(self, source_mode)))
                break

    def __str__(self):
        if (self.mode, self.foreground) not in self.cache:
            if self.foreground:
                base = 30
            else:
                base = 40
            if self.mode == 'color8':
                color = [base + self.color8]
            elif self.mode == 'color256':
                color = [base + 8, 5, self.color256]
            elif self.mode == 'rgb':
                color = [base + 8, 2, *self.rgb]
            elif self.mode == 'grey':
                g = self.grey()
                color = [base + 8, 2, g, g, g]
            else:
                raise TypeError("This should not happen.")
            color = ';'.join(str(_i) for _i in color)
            cstr = f'\033[{color}m'
            self.cache[(self.mode, self.foreground)] = cstr
        return self.cache[(self.mode, self.foreground)]

    def wrap(self, wrapped_str, reset=True):
        """
        wrap some value in format
        :param reset: if reset after wrapped
        :param wrapped_str: wrapped value
        :return: result
        """
        if reset:
            return str(self) + wrapped_str + self.reset
        return str(self) + wrapped_str

    def auto_wrap(self, wrapped_str):
        assert not self.foreground, "Color must be background!"
        if self.grey() >= 128:
            tmp_fore = AnsiColor(color8='black', foreground=True)
        else:
            tmp_fore = AnsiColor(color8='bright white', foreground=True)
        return self.wrap(tmp_fore.wrap(wrapped_str))

    def grey(self, gamma=False):
        r, g, b = self.rgb
        if not gamma:
            return int(0.3 * r + 0.6 * g + 0.1 * b)
        else:
            return int(((r ** 2.2 + (1.5 * g) ** 2.2 + (0.6 * b) ** 2.2) / (
                    1 + 1.5 ** 2.2 + 0.6 ** 2.2)) ** 2.2)  # unknown source

    def square(self):
        return self.wrap('  ')

    def space(self):
        return self.wrap(' ')

if __name__ == '__main__':

    for i in range(256):
        print(AnsiColor(color256=i).auto_wrap('H'), end='' if i % 16 < 15 else '\n')

    for i in range(0, 256, 16):
        for j in range(0, 256, 16):
            for k in range(0, 256, 16):
                print(AnsiColor(r=i,g=j,b=k).space(), end='')
            print(end=' ')
        print()