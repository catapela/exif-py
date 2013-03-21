"""
ExifPy Main Module
"""

# Library to extract Exif information from digital camera image files.
# https://github.com/ianare/exif-py
# https://github.com/rshk/exif-py
#
#
# VERSION 1.2.1
#
# To use this library call with:
#
#    f = open(path_name, 'rb')
#    tags = exifpy.process_file(f)
#
# To ignore MakerNote tags, pass the -q or --quick
# command line arguments, or as
#
#    tags = exifpy.process_file(f, details=False)
#
# To stop processing after a certain tag is retrieved,
# pass the -t TAG or --stop-tag TAG argument, or as
#
#    tags = exifpy.process_file(f, stop_tag='TAG')
#
# where TAG is a valid tag name, ex 'DateTimeOriginal'
#
# These two are useful when you are retrieving a large list of images
#
# To return an error on invalid tags,
# pass the -s or --strict argument, or as
#
#    tags = exifpy.process_file(f, strict=True)
#
# Otherwise these tags will be ignored
#
# Returned tags will be a dictionary mapping names of Exif tags to their
# values in the file named by path_name.  You can process the tags
# as you wish.  In particular, you can iterate through all the tags with:
#     for tag in tags.keys():
#         if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename',
#                        'EXIF MakerNote'):
#             print "Key: %s, value %s" % (tag, tags[tag])
# (This code uses the if statement to avoid printing out a few of the
# tags that tend to be long or boring.)
#
# The tags dictionary will include keys for all of the usual Exif
# tags, and will also include keys for Makernotes used by some
# cameras, for which we have a good specification.
#
# Note that the dictionary keys are the IFD name followed by the
# tag name. For example:
# 'EXIF DateTimeOriginal', 'Image Orientation', 'MakerNote FocusMode'


## See the 'LICENSE' file for licensing information
## See the 'changes.txt' file for all contributors and changes


import logging
from exifpy.constants.tags import EXIF_TAGS, GPS_TAGS, INTR_TAGS
from exifpy.constants.field_types import FIELD_TYPES
from exifpy.utils import make_string, bytebuffer
from exifpy.objects import ExifHeader

logger = logging.getLogger('exifpy')


__all__ = ['process_file']


def _get_offset_endian_tiff(f):
    # it's a TIFF file
    f.seek(0)
    endian = f.read(1)
    f.read(1)
    offset = 0
    return offset, endian


def _get_offset_endian_jpeg(f):
    # it's a JPEG file

    logger.debug("JPEG format recognized data[0:2] == '0xFFD8'.")

    f.seek(0)
    data = bytearray(f.read(12))
    base = 2

    while data[2] == '\xFF' and data[6:10] in ('JFIF', 'JFXX', 'OLYM', 'Phot'):
        logger.debug("data[2] == 0xxFF data[3]==%x and data[6:10] = %s" % (
            ord(data[3]), data[6:10]))
        length = ord(data[4]) * 256 + ord(data[5])
        logger.debug("Length offset is", length)
        f.read(length - 8)
        # fake an EXIF beginning of file
        # I don't think this is used. --gd
        data = '\xFF\x00' + f.read(10)
        #fake_exif = 1
        if base > 2:
            logger.debug("added to base ")
            #base = base + length + 4 - 2
            base += length + 2
        else:
            logger.debug("added to zero ")
            base = length + 4
        logger.debug("Set segment base to {}".format(base))

    # Big ugly patch to deal with APP2 (or other) data coming before APP1
    # In theory, this could be insufficient since 64K is the maximum
    # size --gd

    f.seek(0)
    data = bytearray(f.read(base + 4000))

    ## todo: can't we do this better? like, read only what's needed, ...

    # base = 2
    while True:
        logger.debug("Segment base 0x{:X}".format(base))

        b = bytebuffer(data, base)
        _data_b0t2 = b[:2]

        if _data_b0t2 == '\xFF\xE0':
            ## APP0
            logger.debug("APP0 at 0x{:X}".format(base))
            logger.debug("Length {:x} {:x}".format(b[2], b[3]))
            logger.debug("Code: {}".format(b[4:8]))

        elif _data_b0t2 == '\xFF\xE1':
            ## APP1
            logger.debug("APP1 at 0x{:X}".format(base))
            logger.debug("Length {:x} {:x}".format(b[2], b[3]))
            logger.debug("Code: {}".format(b[4:8]))
            if b[4:8] == "Exif":
                logger.debug("Decrement base by 2 to get to pre-segment "
                             "header (for compatibility with later code)")
                base -= 2
                break

        elif _data_b0t2 == '\xFF\xE2':
            ## APP2
            logger.debug("APP2 at 0x{:X}".format(base))
            logger.debug("Length {:x} {:x}".format(b[2], b[3]))
            logger.debug("Code: {}".format(b[4:8]))

        elif _data_b0t2 == '\xFF\xEE':
            # APP14
            logger.debug("APP14 (Adobe segment) at 0x{:X}".format(base))
            logger.debug("Length {:x} {:x}".format(b[2], b[3]))
            logger.debug("Code: {}".format(b[4:8]))
            logger.debug("There is useful EXIF-like data here, but we "
                         "have no parser for it.")

        elif _data_b0t2 == '\xFF\xD8':
            ## APP12
            logger.debug("FFD8 segment at 0x{:X}".format(base))
            logger.debug("Got {:x} {:x} and {:x} instead"
                         "".format(b[0], b[1], b[4:10]))
            logger.debug("Length {:x} {:x}".format(b[2], b[3]))
            logger.debug("Code: {}".format(b[4:8]))

        elif _data_b0t2 == '\xFF\xEC':
            ## APP12
            logger.debug("APP12 XMP (Ducky) or Pictureinfo segment "
                         "at 0x{:X}".format(base))
            logger.debug("Got {:x} {:x} and {:x} instead"
                         "".format(b[0], b[1], b[4:10]))
            logger.debug("Length {:x} {:x}".format(b[2], b[3]))
            logger.debug("Code: {}".format(b[4:8]))
            logger.debug(
                "There is useful EXIF-like data here (quality, "
                "comment, copyright), but we have no parser for it.")

        elif _data_b0t2 == '\xFF\xDB':
            logger.debug("JPEG image data at 0x{:X}."
                         "No more segments are expected.".format(base))
            break

        else:
            logger.debug("Unexpected/unhandled segment type "
                         "or file content.")

            ## Note: this thing was wrapped in a ``try .. except``
            ## I unwrapped to try and see which exception is raised
            ## (if any) and why..

            _b0 = ord(data[base])
            _b1 = ord(b[1])
            _code2 = b[4:10]
            logger.debug("Got {:x} {:x} and {:x} instead"
                         "".format(_b0, _b1, _code2))

        ## Increment the base..
        _base_increment = (ord(b[2]) * 256) + ord(b[3]) + 2
        logger.debug("Increment base by {}".format(_base_increment))
        base += _base_increment

    ## Jump ahead after file headers..
    f.seek(base + 12)

    b = bytebuffer(data, base)
    _data_b2 = b[2]
    _data_b6t10 = b[6:10]
    _data_b6t11 = b[6:11]

    if _data_b2 == 0xFF:

        if _data_b6t10 == 'Exif':
            ## detected EXIF header
            offset = f.tell()
            endian = f.read(1)
            return offset, endian
            #HACK TEST:  endian = 'M'

        elif _data_b6t11 == 'Ducky':
            ## detected Ducky header.
            logger.debug("EXIF-like header (normally 0xFF and code): "
                         "{:x} and {}".format(_data_b2, _data_b6t11))
            offset = f.tell()
            endian = f.read(1)
            return offset, endian

        elif _data_b6t11 == 'Adobe':
            ## detected APP14 (Adobe)
            logger.debug("EXIF-like header (normally 0xFF and code): "
                         "{:x} and {}".format(_data_b2, _data_b6t11))
            offset = f.tell()
            endian = f.read(1)
            return offset, endian

    else:
        ## No EXIF information found -- error!!
        logger.debug(
            "No EXIF header found:\n"
            "    Expected b[2]==0xFF and b[6:10]=='Exif'' (or 'Duck')\n"
            "    Got: {:x} and {}".format(_data_b2, _data_b6t11))
        raise TypeError("No EXIF header found")


def _get_offset_endian(f):
    """Get offset and endian type from a TIFF or JPEG file"""

    f.seek(0)
    data = bytearray(f.read(12))

    if data[0:4] in ('II*\x00', 'MM\x00*'):
        return _get_offset_endian_tiff(f)

    elif data[0:2] == '\xFF\xD8':
        return _get_offset_endian_jpeg(f)

    raise TypeError("Unrecognised file format")


def process_file(file_obj, stop_tag='UNDEF', details=True, strict=False):
    """
    process an image file (expects an open file object)
    this is the function that has to deal with all the arbitrary nasty bits
    of the EXIF standard.

    :param file_obj:
    :param stop_tag:
    :param details:
    :param strict:
    :return: A dict containing the extracted EXIF tags.
    """

    ## To replace everything down there....
    offset, endian = _get_offset_endian(file_obj)

    ENDIAN_FORMATS = {
        'I': 'Intel',
        'M': 'Motorola',
        '\x01': 'Adobe Ducky',
        'd': 'XMP/Adobe unknown',
    }

    logger.debug("Endian format is {} ({})".format(
        endian, ENDIAN_FORMATS.get(endian, 'unknown')))

    hdr = ExifHeader(file_obj, endian=endian, offset=offset, fake_exif=False,
                     strict=strict, detailed=details)

    # ifd_list = hdr.list_IFDs()
    # ctr = 0
    # thumb_ifd = None
    #
    # for i in ifd_list:
    #     if ctr == 0:
    #         IFD_name = 'Image'
    #     elif ctr == 1:
    #         IFD_name = 'Thumbnail'
    #         thumb_ifd = i
    #     else:
    #         IFD_name = 'IFD %d' % ctr
    #     logger.debug(' IFD %d (%s) at offset %d:' % (ctr, IFD_name, i))
    #     hdr.dump_IFD(i, IFD_name, stop_tag=stop_tag)
    #
    #     ## EXIF IFD
    #     exif_offset = hdr.tags.get(IFD_name + ' ExifOffset')
    #     if exif_offset:
    #         logger.debug(' EXIF SubIFD at offset %d:' % exif_offset.values[0])
    #         hdr.dump_IFD(exif_offset.values[0], 'EXIF', stop_tag=stop_tag)
    #         # Interoperability IFD contained in EXIF IFD
    #         intr_offset = hdr.tags.get('EXIF SubIFD InteroperabilityOffset')
    #         if intr_offset:
    #             logger.debug(' EXIF Interoperability SubSubIFD at offset {:d}:'
    #                          ''.format(intr_offset.values[0]))
    #             hdr.dump_IFD(intr_offset.values[0], 'EXIF Interoperability',
    #                          exif_tags=INTR_TAGS, stop_tag=stop_tag)
    #
    #     ## GPS IFD
    #     gps_offset = hdr.tags.get(IFD_name + ' GPSInfo')
    #     if gps_offset:
    #         logger.debug(' GPS SubIFD at offset %d:' % gps_offset.values[0])
    #         hdr.dump_IFD(gps_offset.values[0], 'GPS', exif_tags=GPS_TAGS,
    #                      stop_tag=stop_tag)
    #     ctr += 1
    #
    # ## Extract uncompressed TIFF thumbnail
    # thumb = hdr.tags.get('Thumbnail Compression')
    # if thumb_ifd is not None \
    #         and thumb \
    #         and thumb.printable == 'Uncompressed TIFF':
    #     hdr.extract_TIFF_thumbnail(thumb_ifd)
    #
    # ## JPEG thumbnail (thankfully the JPEG data is stored as a unit)
    # thumb_off = hdr.tags.get('Thumbnail JPEGInterchangeFormat')
    # if thumb_off:
    #     file_obj.seek(offset + thumb_off.values[0])
    #     size = hdr.tags['Thumbnail JPEGInterchangeFormatLength'].values[0]
    #     hdr.tags['JPEGThumbnail'] = file_obj.read(size)
    #
    # ## Deal with MakerNote contained in EXIF IFD
    # ## (Some apps use MakerNote tags but do not use a format for which we
    # ## have a description, do not process these).
    # if details and \
    #         ('EXIF MakerNote' in hdr.tags) and \
    #         ('Image Make' in hdr.tags):
    #     hdr.decode_maker_note()
    #
    # ## Sometimes in a TIFF file, a JPEG thumbnail is hidden in the MakerNote
    # ## since it's not allowed in a uncompressed TIFF IFD
    # if 'JPEGThumbnail' not in hdr.tags:
    #     thumb_off = hdr.tags.get('MakerNote JPEGThumbnail')
    #     if thumb_off:
    #         file_obj.seek(offset + thumb_off.values[0])
    #         hdr.tags['JPEGThumbnail'] = file.read(thumb_off.field_length)
    #
    # return hdr.tags

    return hdr
