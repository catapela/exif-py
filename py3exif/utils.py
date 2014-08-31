"""
py3exif Utilities
"""
import os
import logging
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
    if size == 0:
        return 'B'
    elif size == 1:
        fmt += 'B' if not signed else 'b'
    elif size == 2:
        fmt += 'H' if not signed else 'h'
    elif size == 4:
        fmt += 'I' if not signed else 'i'
    elif size == 8:
        fmt += 'Q' if not signed else 'q'
    else:
        logging.error("Unsupported non-standard size (got: {})".format(size))
        raise ValueError("Unsupported non-standard size (got: {})".format(size))
    return fmt


def decode_int(input_string, signed=False, little_endian=True):
    size = len(input_string)
    if size == 0:
        return 0
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


class FileSeek(object):
    def __init__(self, fileobj, pos=0, from_what=0):
        self._fileobj = fileobj
        self._pos = pos
        self._from_what = from_what

    def __enter__(self):
        self._prev_pos = self._fileobj.tell()
        self._fileobj.seek(self._pos, self._from_what)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._fileobj.seek(self._prev_pos)


class FileWindow(object):
    """
    A "window" over a file object
    """

    def __init__(self, fileobj, start=None, end=None):
        self._fileobj = fileobj
        self.set_window(start, end)

    @property
    def file_size(self):
        with FileSeek(self._fileobj, 0, os.SEEK_END):
            return self._fileobj.tell()

    @property
    def win_size(self):
        return self._end - self._start

    def set_window(self, start=None, end=None):
        if start is None:
            start = 0
        if start < 0:
            start += self.file_size
        if end is None:
            end = self.file_size
        if end < 0:
            end += self.file_size
        if start > end:
            raise ValueError("Start cannot be > end!")
        self._start = start
        self._end = end

    def __getattr__(self, item):
        wrapped_attrs = (
            'close', 'flush', 'fileno', 'isatty', 'closed', 'encoding',
            'errors', 'mode', 'name', 'newlines', 'softspace')
        notimplemented_attrs = (
            'readline', 'readlines', 'xreadlines', 'truncate', 'write',
            'writelines')
        if item in wrapped_attrs:
            return getattr(self._fileobj, item)
        if item in notimplemented_attrs:
            raise NotImplementedError(
                "Method {} is not implemented".format(item))
        raise AttributeError(item)

    def next(self):
        raise NotImplementedError

    def read(self, size=None):
        max_readable = max(0, self.win_size - self.tell())
        if (size is None) or (size > max_readable):
            size = max_readable
        retval = self._fileobj.read(size)
        return retval

    def seek(self, pos=None, from_where=os.SEEK_SET):
        if pos is None:
            pos = 0

        if from_where == os.SEEK_SET:
            self._fileobj.seek(pos + self._start)

        elif from_where == os.SEEK_CUR:
            self._fileobj.seek(pos, os.SEEK_CUR)

        elif from_where == os.SEEK_END:
            self._fileobj.seek(pos + self._end)

        else:
            raise ValueError("Invalid from_where argument (must be os.SEEK_*)")

        if self._fileobj.tell() < self._start:
            self._fileobj.seek(self._start)

    def tell(self):
        return self._fileobj.tell() - self._start


class mmapbytes(object):
    """
    MMAP-Like object that works on any kind of file-like.
    Acts in a way similar to a ``bytearray()`` spanning the whole
    file (or a certain part of it).

    We cannot use a mmap here, since the image may not be in a real
    file, with a file descriptor etc.
    """

    def __init__(self, fileobj, offset=None, limit=None):
        self._fileobj = FileWindow(fileobj, offset, limit)

    def set_window(self, offset=None, limit=None):
        return self._fileobj.set_window(offset, limit)

    def _get_file_slice(self, start, end):
        if start is None:
            start = 0

        from_what = os.SEEK_END if start < 0 else os.SEEK_SET

        if end is None:
            size = None
        else:
            size = end - start

        with FileSeek(self._fileobj, start, from_what=from_what):
            return self._fileobj.read(size)

    def _get_file_char(self, pos):
        if abs(pos) > self._fileobj.win_size:
            # As the FileWindow will (correctly) seek() to index 0
            raise IndexError("Index out of range")
        return self._get_file_slice(pos, pos + 1)

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.step is not None:
                raise NotImplementedError(
                    "Slicing file with step is not supported")

            sliced = self._get_file_slice(item.start, item.stop)
            return sliced

        else:
            byte = self._get_file_char(item)
            if not byte:
                raise IndexError("EOF reached")
            return ord(byte)

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
