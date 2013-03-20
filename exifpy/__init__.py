#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#
# Library to extract Exif information from digital camera image files.
# https://github.com/ianare/exif-py
#
#
# VERSION 1.2.0
#
# To use this library call with:
#    f = open(path_name, 'rb')
#    tags = EXIF.process_file(f)
#
# To ignore MakerNote tags, pass the -q or --quick
# command line arguments, or as
#    tags = EXIF.process_file(f, details=False)
#
# To stop processing after a certain tag is retrieved,
# pass the -t TAG or --stop-tag TAG argument, or as
#    tags = EXIF.process_file(f, stop_tag='TAG')
#
# where TAG is a valid tag name, ex 'DateTimeOriginal'
#
# These two are useful when you are retrieving a large list of images
#
# To return an error on invalid tags,
# pass the -s or --strict argument, or as
#    tags = EXIF.process_file(f, strict=True)
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
from exifpy.constants.tags import *
from exifpy.constants.field_types import FIELD_TYPES
from exifpy.utils import *
from exifpy.objects import *

logger = logging.getLogger('exifpy')
logger.debug('Hello')


# field type descriptions as (length, abbreviation, full name) tuples


def process_file(f, stop_tag='UNDEF', details=True, strict=False, debug=False):
    """
    process an image file (expects an open file object)
    this is the function that has to deal with all the arbitrary nasty bits
    of the EXIF standard
    """
    # yah it's cheesy...
    global detailed  ## <--- yeah, dafuq?
    detailed = details

    # by default do not fake an EXIF beginning
    fake_exif = 0

    # determine whether it's a JPEG or TIFF
    data = f.read(12)
    if data[0:4] in ['II*\x00', 'MM\x00*']:
        # it's a TIFF file
        f.seek(0)
        endian = f.read(1)
        f.read(1)
        offset = 0
    elif data[0:2] == '\xFF\xD8':
        # it's a JPEG file
        if debug: print("JPEG format recognized data[0:2] == '0xFFD8'.")
        base = 2
        while data[2] == '\xFF' and data[6:10] in ('JFIF', 'JFXX', 'OLYM', 'Phot'):
            if debug: print("data[2] == 0xxFF data[3]==%x and data[6:10] = %s"%(ord(data[3]),data[6:10]))
            length = ord(data[4])*256+ord(data[5])
            if debug: print("Length offset is",length)
            f.read(length-8)
            # fake an EXIF beginning of file
            # I don't think this is used. --gd
            data = '\xFF\x00'+f.read(10)
            fake_exif = 1
            if base>2:
                if debug: print("added to base ")
                base = base + length + 4 -2
            else:
                if debug: print("added to zero ")
                base = length + 4
            if debug: print("Set segment base to",base)

        # Big ugly patch to deal with APP2 (or other) data coming before APP1
        f.seek(0)
        data = f.read(base+4000) # in theory, this could be insufficient since 64K is the maximum size--gd
        # base = 2
        while 1:
            if debug: print("Segment base 0x%X" % base)
            if data[base:base+2]=='\xFF\xE1':
                # APP1
                if debug: print("APP1 at base",hex(base))
                if debug: print("Length",hex(ord(data[base+2])), hex(ord(data[base+3])))
                if debug: print("Code",data[base+4:base+8])
                if data[base+4:base+8] == "Exif":
                    if debug: print("Decrement base by",2,"to get to pre-segment header (for compatibility with later code)")
                    base = base-2
                    break
                if debug: print("Increment base by",ord(data[base+2])*256+ord(data[base+3])+2)
                base=base+ord(data[base+2])*256+ord(data[base+3])+2
            elif data[base:base+2]=='\xFF\xE0':
                # APP0
                if debug: print("APP0 at base",hex(base))
                if debug: print("Length",hex(ord(data[base+2])), hex(ord(data[base+3])))
                if debug: print("Code",data[base+4:base+8])
                if debug: print("Increment base by",ord(data[base+2])*256+ord(data[base+3])+2)
                base=base+ord(data[base+2])*256+ord(data[base+3])+2
            elif data[base:base+2]=='\xFF\xE2':
                # APP2
                if debug: print("APP2 at base",hex(base))
                if debug: print("Length",hex(ord(data[base+2])), hex(ord(data[base+3])))
                if debug: print("Code",data[base+4:base+8])
                if debug: print("Increment base by",ord(data[base+2])*256+ord(data[base+3])+2)
                base=base+ord(data[base+2])*256+ord(data[base+3])+2
            elif data[base:base+2]=='\xFF\xEE':
                # APP14
                if debug: print("APP14 Adobe segment at base",hex(base))
                if debug: print("Length",hex(ord(data[base+2])), hex(ord(data[base+3])))
                if debug: print("Code",data[base+4:base+8])
                if debug: print("Increment base by",ord(data[base+2])*256+ord(data[base+3])+2)
                print("There is useful EXIF-like data here, but we have no parser for it.")
                base=base+ord(data[base+2])*256+ord(data[base+3])+2
            elif data[base:base+2]=='\xFF\xDB':
                if debug: print("JPEG image data at base",hex(base),"No more segments are expected.")
                # sys.exit(0)
                break
            elif data[base:base+2]=='\xFF\xD8':
                # APP12
                if debug: print("FFD8 segment at base",hex(base))
                if debug: print("Got",hex(ord(data[base])), hex(ord(data[base+1])),"and", data[4+base:10+base], "instead.")
                if debug: print("Length",hex(ord(data[base+2])), hex(ord(data[base+3])))
                if debug: print("Code",data[base+4:base+8])
                if debug: print("Increment base by",ord(data[base+2])*256+ord(data[base+3])+2)
                base=base+ord(data[base+2])*256+ord(data[base+3])+2
            elif data[base:base+2]=='\xFF\xEC':
                # APP12
                if debug: print("APP12 XMP (Ducky) or Pictureinfo segment at base",hex(base))
                if debug: print("Got",hex(ord(data[base])), hex(ord(data[base+1])),"and", data[4+base:10+base], "instead.")
                if debug: print("Length",hex(ord(data[base+2])), hex(ord(data[base+3])))
                if debug: print("Code",data[base+4:base+8])
                if debug: print("Increment base by",ord(data[base+2])*256+ord(data[base+3])+2)
                print("There is useful EXIF-like data here (quality, comment, copyright), but we have no parser for it.")
                base=base+ord(data[base+2])*256+ord(data[base+3])+2
            else:
                try:
                    if debug: print("Unexpected/unhandled segment type or file content.")
                    if debug: print("Got",hex(ord(data[base])), hex(ord(data[base+1])),"and", data[4+base:10+base], "instead.")
                    if debug: print("Increment base by",ord(data[base+2])*256+ord(data[base+3])+2)
                except: pass
                try: base=base+ord(data[base+2])*256+ord(data[base+3])+2
                except: return {}
        f.seek(base+12)
        if data[2+base] == '\xFF' and data[6+base:10+base] == 'Exif':
            # detected EXIF header
            offset = f.tell()
            endian = f.read(1)
            #HACK TEST:  endian = 'M'
        elif data[2+base] == '\xFF' and data[6+base:10+base+1] == 'Ducky':
            # detected Ducky header.
            if debug: print("EXIF-like header (normally 0xFF and code):",hex(ord(data[2+base])) , "and", data[6+base:10+base+1])
            offset = f.tell()
            endian = f.read(1)
        elif data[2+base] == '\xFF' and data[6+base:10+base+1] == 'Adobe':
            # detected APP14 (Adobe)
            if debug: print("EXIF-like header (normally 0xFF and code):",hex(ord(data[2+base])) , "and", data[6+base:10+base+1])
            offset = f.tell()
            endian = f.read(1)
        else:
            # no EXIF information
            if debug: print("No EXIF header expected data[2+base]==0xFF and data[6+base:10+base]===Exif (or Duck)")
            if debug: print(" but got",hex(ord(data[2+base])) , "and", data[6+base:10+base+1])
            return {}
    else:
        # file format not recognized
        if debug: print("file format not recognized")
        return {}

    # deal with the EXIF info we found
    if debug:
        print("Endian format is ",endian)
        print({'I': 'Intel', 'M': 'Motorola', '\x01':'Adobe Ducky', 'd':'XMP/Adobe unknown' }[endian], 'format')
    hdr = EXIF_header(f, endian, offset, fake_exif, strict, debug)
    ifd_list = hdr.list_IFDs()
    ctr = 0
    for i in ifd_list:
        if ctr == 0:
            IFD_name = 'Image'
        elif ctr == 1:
            IFD_name = 'Thumbnail'
            thumb_ifd = i
        else:
            IFD_name = 'IFD %d' % ctr
        if debug:
            print(' IFD %d (%s) at offset %d:' % (ctr, IFD_name, i))
        hdr.dump_IFD(i, IFD_name, stop_tag=stop_tag)
        # EXIF IFD
        exif_off = hdr.tags.get(IFD_name+' ExifOffset')
        if exif_off:
            if debug:
                print(' EXIF SubIFD at offset %d:' % exif_off.values[0])
            hdr.dump_IFD(exif_off.values[0], 'EXIF', stop_tag=stop_tag)
            # Interoperability IFD contained in EXIF IFD
            intr_off = hdr.tags.get('EXIF SubIFD InteroperabilityOffset')
            if intr_off:
                if debug:
                    print(' EXIF Interoperability SubSubIFD at offset %d:' \
                          % intr_off.values[0])
                hdr.dump_IFD(intr_off.values[0], 'EXIF Interoperability',
                             dict=INTR_TAGS, stop_tag=stop_tag)
            # GPS IFD
        gps_off = hdr.tags.get(IFD_name+' GPSInfo')
        if gps_off:
            if debug:
                print(' GPS SubIFD at offset %d:' % gps_off.values[0])
            hdr.dump_IFD(gps_off.values[0], 'GPS', dict=GPS_TAGS, stop_tag=stop_tag)
        ctr += 1

    # extract uncompressed TIFF thumbnail
    thumb = hdr.tags.get('Thumbnail Compression')
    if thumb and thumb.printable == 'Uncompressed TIFF':
        hdr.extract_TIFF_thumbnail(thumb_ifd)

    # JPEG thumbnail (thankfully the JPEG data is stored as a unit)
    thumb_off = hdr.tags.get('Thumbnail JPEGInterchangeFormat')
    if thumb_off:
        f.seek(offset+thumb_off.values[0])
        size = hdr.tags['Thumbnail JPEGInterchangeFormatLength'].values[0]
        hdr.tags['JPEGThumbnail'] = f.read(size)

    # deal with MakerNote contained in EXIF IFD
    # (Some apps use MakerNote tags but do not use a format for which we
    # have a description, do not process these).
    if 'EXIF MakerNote' in hdr.tags and 'Image Make' in hdr.tags and detailed:
        hdr.decode_maker_note()

    # Sometimes in a TIFF file, a JPEG thumbnail is hidden in the MakerNote
    # since it's not allowed in a uncompressed TIFF IFD
    if 'JPEGThumbnail' not in hdr.tags:
        thumb_off=hdr.tags.get('MakerNote JPEGThumbnail')
        if thumb_off:
            f.seek(offset+thumb_off.values[0])
            hdr.tags['JPEGThumbnail']=file.read(thumb_off.field_length)

    return hdr.tags
