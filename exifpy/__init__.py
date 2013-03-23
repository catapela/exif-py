"""
ExifPy Main Module
"""

## Library to extract Exif information from digital camera image files.
## https://github.com/ianare/exif-py
## https://github.com/rshk/exif-py

## VERSION 1.2.1

## See the 'LICENSE' file for licensing information
## See the 'changes.txt' file for all contributors and changes


import logging
from exifpy.constants.tags import EXIF_TAGS, GPS_TAGS, INTR_TAGS, ENDIAN_FORMATS
from exifpy.constants.field_types import FIELD_TYPES
from exifpy.exceptions import UnsupportedFormat, NoExifData
from exifpy.utils import make_string, mmapbytes
from exifpy.objects import ExifHeader

logger = logging.getLogger('exifpy')

__all__ = ['process_file']


def _get_offset_endian_tiff(f):
    ## it's a TIFF file
    f.seek(0)
    endian = f.read(1)
    f.read(1)
    offset = 0
    return offset, endian


def _get_offset_endian_jpeg(f):
    ## it's a JPEG file

    logger.debug("JPEG format recognized data[0:2] == '0xFFD8'.")

    ## Determine the "base" from which to start reading
    f.seek(0)
    data = bytearray(f.read(12))
    base = 2
    while data[2] == 0xFF and data[6:10] in ('JFIF', 'JFXX', 'OLYM', 'Phot'):
        logger.debug("data[2] == 0xFF data[3] == {:x} and data[6:10] = {}"
                     "".format(data[3], data[6:10]))
        length = (data[4] * 256) + data[5]
        assert isinstance(length, int)
        logger.debug("Length offset is {:d}".format(length))
        f.read(length - 8)
        ## Fake an EXIF beginning of file
        ## I don't think this is used. --gd
        data = '\xFF\x00' + f.read(10)
        #fake_exif = 1
        if base > 2:
            logger.debug("added to base")
            base += length + 2
        else:
            logger.debug("added to zero")
            base = length + 4
        logger.debug("Set segment base to {}".format(base))

    del data  # We're done with it!!

    b = mmapbytes(f)
    while True:
        logger.debug("Segment base 0x{:X}".format(base))
        b.set_window(base)
        b1 = b[1]
        if b[0] == 0xFF:
            if b1 == 0xE1:
                if b[4:8] == "Exif":
                    base -= 2
                break
            if b1 == 0xDB:
                break
        _base_increment = (b[2] * 256) + b[3] + 2
        logger.debug("Increment base by {}".format(_base_increment))
        base += _base_increment

    ## Jump ahead after file headers
    b.set_window(base)
    _data_b2 = b[2]
    _data_b6t10 = b[6:10]
    _data_b6t11 = b[6:11]

    if _data_b2 == 0xFF:

        logger.debug("Exif header: {:x} {!r}".format(_data_b2, _data_b6t11))

        if _data_b6t10 == 'Exif':
            ## detected EXIF header
            offset = f.tell()
            endian = f.read(1)
            return offset, endian
            #HACK TEST:  endian = 'M'

        elif _data_b6t11 == 'Ducky':
            ## detected Ducky header.
            logger.debug("EXIF-like header (normally 0xFF and code): "
                         "{:x} and {!r}".format(_data_b2, _data_b6t11))
            offset = f.tell()
            endian = f.read(1)
            return offset, endian

        elif _data_b6t11 == 'Adobe':
            ## detected APP14 (Adobe)
            logger.debug("EXIF-like header (normally 0xFF and code): "
                         "{:x} and {!r}".format(_data_b2, _data_b6t11))
            offset = f.tell()
            endian = f.read(1)
            return offset, endian
    else:
        ## No EXIF information found -- error!!
        logger.debug(
            "No EXIF header found:\n"
            "    Expected b[2]==0xFF and b[6:10]=='Exif'' (or 'Duck')\n"
            "    Got: {:x} and {!r}".format(_data_b2, _data_b6t11))
        raise NoExifData("No EXIF header found")


def _get_offset_endian(f):
    """Get offset and endian type from a TIFF or JPEG file"""

    f.seek(0)
    data = bytearray(f.read(12))

    if data[0:4] in ('II*\x00', 'MM\x00*'):
        ## This is a TIFF file
        return _get_offset_endian_tiff(f)

    elif data[0:2] == '\xFF\xD8':
        ## This is a JPEG file
        return _get_offset_endian_jpeg(f)

    raise UnsupportedFormat("Unrecognised file format")


def process_file(file_obj, detailed=True, strict=False):
    """
    Process an image file (expects an open file object)
    this is the function that has to deal with all the arbitrary nasty bits
    of the EXIF standard.

    :param file_obj: File object from which to read
    :param detailed: Whether to add "detailed" tag information.
        Defaults to True.
    :param strict: Whether to run in "strict mode", raising
        more exceptions upon failure
    :return: An ExifHeader object (dict-like) containing the extracted
        EXIF tags (or, extracting them on-the-fly).
    """

    offset, endian = _get_offset_endian(file_obj)

    logger.debug("File endian format is {} ({})"
                 "".format(endian, ENDIAN_FORMATS.get(endian, 'unknown')))

    return ExifHeader(
        file_obj,
        endian=endian,
        offset=offset,
        strict=strict,
        detailed=detailed)
