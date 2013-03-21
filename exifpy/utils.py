"""
ExifPy Utilities
"""

__all__ = ['make_string', 'make_string_uc', 'gcd', 's2n_intel', 's2n_motorola',
           'bytebuffer']


def make_string(seq):
    """
    Don't throw an exception when given an out of range character.
    """
    # todo: this can be done way more efficiently!!
    new_string = ''
    for c in seq:
        # Screen out non-printing characters
        if 32 <= c < 256:
            new_string += chr(c)
            # If no printing chars
    if not new_string:
        return seq
    return new_string


def make_string_uc(seq):
    """
    Special version to deal with the code in the first 8 bytes of a
    user comment.
    First 8 bytes gives coding system e.g. ASCII vs. JIS vs Unicode
    """
    # code = seq[0:8]
    seq = seq[8:]
    # Of course, this is only correct if ASCII, and the standard explicitly
    # allows JIS and Unicode.
    return make_string(make_string(seq))


def s2n_motorola(input_string):
    """
    Extract multibyte integer in Motorola format (little endian)
    """
    x = 0
    for c in input_string:
        x = (x << 8) | ord(c)
    return x


def s2n_intel(input_string):
    """
    Extract multibyte integer in Intel format (big endian)
    """
    x = 0
    y = 0
    for c in input_string:
        x |= ord(c) << y
        y += 8
    return x


def gcd(a, b):
    """
    Ratio object that eventually will be able to reduce itself to lowest
    common denominator for printing
    """
    if b == 0:
        return a
    else:
        return gcd(b, a % b)


class bytebuffer(object):
    """
    Kind-of buffer() that works on bytearray().
    """

    def __init__(self, obj, delta=0):
        self._obj = obj
        self._delta = delta

    def __getitem__(self, item):
        if isinstance(item, slice):

            if item.start is None:
                start = self._delta
            else:
                start = item.start + self._delta

            if item.stop is None:
                stop = None  # The end is the end, my friend..
            else:
                stop = item.stop + self._delta

            s = slice(start, stop, item.step)
            return self._obj[s]

        else:
            return self._obj[item]

    def __setitem__(self, key, value):
        raise NotImplementedError

    def __delitem__(self, key):
        raise NotImplementedError
