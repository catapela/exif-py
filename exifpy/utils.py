"""
ExifPy Utilities
"""

import struct


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


def _get_pack_format(size=4, signed=False, little_endian=False):
    fmt = ''
    fmt += '<' if little_endian else '>'
    if size == 1:
        fmt += 'B' if not signed else 'b'
    elif size == 2:
        fmt += 'H' if not signed else 'h'
    elif size == 4:
        fmt += 'I' if not signed else 'i'
    elif size == 8:
        fmt += 'Q' if not signed else 'q'
    else:
        raise ValueError("Unsupported non-standard size!")
    return fmt


def decode_int(input_string, signed=False, little_endian=True):
    size = len(input_string)
    fmt = _get_pack_format(size=size, signed=signed,
                           little_endian=little_endian)
    return struct.unpack(fmt, input_string)[0]


def encode_int(number, size=4, signed=False, little_endian=True):
    fmt = _get_pack_format(size=size, signed=signed,
                           little_endian=little_endian)
    return struct.pack(fmt, number)


def unpack_motorola(input_string, signed=False):
    """Extract multibyte integer in Motorola format (big endian)"""
    return decode_int(input_string, signed=signed, little_endian=False)


def unpack_intel(input_string, signed=False):
    """Extract multibyte integer in Intel format (little endian)"""
    return decode_int(input_string, signed=signed, little_endian=True)


def pack_intel(input_number, length=4, signed=False):
    """Convert int to little-endian-packed string"""
    return encode_int(input_number, size=length, signed=signed,
                      little_endian=True)


def pack_motorola(input_number, length=4, signed=False):
    """Convert int to big-endian-packed string"""
    return encode_int(input_number, size=length, signed=signed,
                      little_endian=False)


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

            #s = slice(start, stop, item.step)
            return self._obj[start:stop:item.step]

        else:
            # return self._obj[item]
            return self._obj[item + self._delta]

    def __setitem__(self, key, value):
        raise NotImplementedError

    def __delitem__(self, key):
        raise NotImplementedError


def lazy_property(fn):
    attr_name = '_lazy_' + fn.__name__

    def getter(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)

    def setter(self, value):
        setattr(self, attr_name, value)

    def deleter(self):
        delattr(self, attr_name)

    return property(fget=getter, fset=setter, fdel=deleter, doc=fn.__doc__)
