"""
Tests all the utilities
"""

import unittest


class DummyTest(unittest.TestCase):
    def test_nothing(self):
        pass

    def test_read_intel_unsigned_int(self):
        ## Read from little endian (Intel) format
        from exifpy.utils import unpack_intel
        self.assertEqual(unpack_intel('\xE8\x03'), 1000)

    def test_read_intel_signed_int(self):
        ## Read from big endian (Motorola) format
        from exifpy.utils import unpack_motorola
        self.assertEqual(unpack_motorola('\x03\xE8'), 1000)

    def test_encdec_int(self):
        from exifpy.utils import encode_int, decode_int

        def test_encdec(number, size, signed, little_endian):
            result = encode_int(number, size=size, signed=signed,
                                little_endian=little_endian)
            result2 = decode_int(result, signed=signed,
                                 little_endian=little_endian)
            self.assertEqual(number, result2)

        ## Check with fixed values..
        self.assertEqual(decode_int('\xE8\x03', little_endian=True), 1000)

        ## This is a big endian 1000...
        self.assertEqual(decode_int('\x03\xE8', little_endian=False), 1000)

        ## Check reciprocity..
        test_encdec(1000, 4, False, False)
        test_encdec(1000, 4, True, False)
        test_encdec(1000, 4, False, True)
        test_encdec(1000, 4, True, True)

        test_encdec(-1000, 4, True, False)
        test_encdec(-1000, 4, True, True)
