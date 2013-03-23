"""
Tests all the utilities
"""

import unittest


class TestMmapBytes(unittest.TestCase):
    def test_filewindow(self):
        import os
        from StringIO import StringIO
        from exifpy.utils import FileWindow

        s = StringIO("Hello, world; spam & eggs for everybody!")
        s.seek(0)
        self.assertEqual("H", s.read(1))
        self.assertEqual("e", s.read(1))
        self.assertEqual("llo", s.read(3))
        s.seek(-1, os.SEEK_END)
        self.assertEqual("!", s.read(1))

        win0 = FileWindow(s)
        win0.seek(0)
        self.assertEqual("H", win0.read(1))
        self.assertEqual("e", win0.read(1))
        self.assertEqual("llo", win0.read(3))
        win0.seek(-1, os.SEEK_END)
        self.assertEqual("!", win0.read(1))
        win0.seek(-5, os.SEEK_END)
        self.assertEqual("body!", win0.read(5))

        win1 = FileWindow(s, 7)
        win1.seek(0)
        self.assertEqual("w", win1.read(1))
        self.assertEqual("o", win1.read(1))
        self.assertEqual("rld", win1.read(3))
        win1.seek(-1, os.SEEK_END)
        self.assertEqual("!", win1.read(1))
        win1.seek(-5, os.SEEK_END)
        self.assertEqual("body!", win1.read(5))

        win1.set_window(14, 25)
        win1.seek(0)
        self.assertEqual("spam & eggs", win1.read())
        win1.seek(0)
        self.assertEqual("spam", win1.read(4))
        win1.seek(0)
        self.assertEqual("spam & eggs", win1.read(1000))
        win1.seek(-4, os.SEEK_END)
        self.assertEqual("eggs", win1.read(4))
        win1.seek(-4, os.SEEK_END)
        self.assertEqual("eggs", win1.read())
        win1.seek(-4, os.SEEK_END)
        self.assertEqual("eggs", win1.read(1000))

        win2 = FileWindow(s, 14, 25)
        win2.seek(0)
        self.assertEqual("spam & eggs", win2.read())
        win2.seek(0)
        self.assertEqual("spam", win2.read(4))
        win2.seek(0)
        self.assertEqual("spam & eggs", win2.read(1000))
        win2.seek(-4, os.SEEK_END)
        self.assertEqual("eggs", win2.read(4))
        win2.seek(-4, os.SEEK_END)
        self.assertEqual("eggs", win2.read())
        win2.seek(-4, os.SEEK_END)
        self.assertEqual("eggs", win2.read(1000))

    def test_mmapbytes(self):
        from StringIO import StringIO
        from exifpy.utils import mmapbytes

        message = "Hello, world; spam & eggs for everybody!"

        ## Test direct referencing of items
        ## The object should behave exactly like a bytearray

        test_indices = [
            0, 7, 14, -1, -10, -14
        ]
        test_windows = [
            (None, None),
            (0, 0),
            (0, 12),
            (None, 12),
            (14, 0),
            (14, None),
            (14, 25),
        ]

        for winStart, winEnd in test_windows:
            _message = message[winStart:winEnd]
            mm = mmapbytes(StringIO(_message))
            for idx in test_indices:
                try:
                    expected = ord(_message[idx])

                except IndexError:
                    # print "\n\n\nWe're running with window {},{}" \
                    #       "".format(winStart, winEnd)
                    # print "The string {!r} raised IndexError on index {}. "\
                    #     "We expect the mmapbytes() object to do the same."\
                    #     "".format(_message, idx)

                    with self.assertRaises(IndexError):
                        mm[idx]
                        # print "RETURNED {!r}".format(mm[idx])

                else:
                    result = mm[idx]
                    self.assertEqual(
                        expected, result,
                        "Test window {},{} index {} - Expected: {!r} got: {!r}"
                        "".format(winStart, winEnd, idx, expected, result))

        ## Test some slicing.
        ## The object should behave exactly like a string.

        test_indices = [
            (0, 1),
            (0, 10),
            (0, None),
            (None, 0),
            (None, 10),
            (10, None),
            (None, None),
        ]
        test_windows = [
            (None, None),
            (0, 0),
            (0, 12),
            (None, 12),
            (14, 0),
            (14, None),
            (14, 25),
        ]

        for winStart, winEnd in test_windows:
            _message = message[winStart:winEnd]
            mm = mmapbytes(StringIO(_message))
            for start, end in test_indices:
                expected = _message[start:end]
                result = mm[start:end]
                self.assertEqual(
                    expected, result,
                    "Test window {},{} slice {},{} - Expected: {!r} got: {!r}"
                    "".format(winStart, winEnd, start, end, expected, result))
