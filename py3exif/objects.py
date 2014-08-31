"""
Misc objects
"""

import logging
import warnings
import collections

from .constants.tags import *
from .constants.field_types import FIELD_TYPES, FT_ASCII, FT_SIGNED_BYTE, \
    FT_SIGNED_RATIO, FT_SIGNED_LONG, FT_SIGNED_SHORT, FT_RATIO
from py3exif import INTR_TAGS
from .utils import *


logger = logging.getLogger('py3exif')


class Ratio(object):
    def __init__(self, num, den=None):
        if isinstance(num, basestring) and den is None:
            num, den = map(int, num.split('/'))
        self.num = num
        self.den = den

    def __repr__(self):
        self.reduce()
        if self.den == 1:
            return str(self.num)

        try:
            # todo: any better way to do this?
            ratio = float(self)
        except ZeroDivisionError:
            ratio = 0

        return '<Ratio {:d}/{:d} (~{:.2f})>' \
               ''.format(self.num, self.den, ratio)

    def __str__(self):
        return self.__repr__()

    def reduce(self):
        div = gcd(self.num, self.den)
        if div > 1:
            self.num = self.num / div
            self.den = self.den / div

    def __float__(self):
        return float(self.num) / float(self.den)


class IFD_Tag(object):
    """For ease of dealing with tags"""
    def __init__(self, printable=None, tag=None, field_type=0, values=None,
                 field_offset=None, field_length=None, tag_entry=None):

        assert printable is None

        # printable version of data
        # self.printable = printable
        # tag ID number
        self.tag = tag
        # field type as index into FIELD_TYPES
        self.field_type = field_type
        # offset of start of field in bytes from beginning of IFD
        self.field_offset = field_offset
        # length of data field in bytes
        self.field_length = field_length
        # Information on this tag
        self.tag_entry = tag_entry
        # either a string or array of data items
        self._raw_values = values

    def __str__(self):
        return str(self.printable)

    def __repr__(self):
        return "<IFD_Tag 0x{:04x} ({}) {!r} at 0x{:04X}>".format(
            self.tag,
            FIELD_TYPES[self.field_type][2],
            self.printable,
            self.field_offset,
        )

    @lazy_property
    def to_python(self):

        # # Important! We have both per-field and per-type formatters!

        field_type = FIELD_TYPES.get(self.field_type)
        if field_type is None:
            warnings.warn("Unsupported field type {:d}".format(self.field_type))
            converter = lambda x: x
        else:
            converter = field_type[3]

        if isinstance(self._raw_values, (tuple, list)):
            return [converter(x) for x in self._raw_values]
        else:
            return converter(self._raw_values)

    @lazy_property
    def printable(self):
        # # Now 'values' is either a string or an array
        # # todo: WTF???

        # if isinstance(self.values, (list, tuple)):
        #     count = len(self.values)
        # else:
        #     count = 1
        #
        # if count == 1 and self.field_type != FT_ASCII:
        #     printable = str(self.values[0])
        #
        # elif count > 50 and len(self.values) > 20:
        #     printable = str(self.values[0:20])[0:-1] + ", ... ]"
        #
        # else:
        #     printable = str(self.values)

        # # Compute printable version of values
        # # todo: this should be generated by the tag at need...
        if self.tag_entry and len(self.tag_entry) >= 2:
            # # We have a formatter function for this field..

            formatter = self.tag_entry[1]

            if callable(formatter):
                # call mapping function
                printable = formatter(self._raw_values)

            else:
                printable = ', '.join(
                    (formatter.get(i) or repr(i)) for i in self._raw_values)

            return printable

        return self._raw_values

    @property
    def values(self):
        return self._raw_values

    @property
    def value(self):
        vl = len(self._raw_values)
        if vl == 0:
            return None
        elif vl > 1:
            warnings.warn("Assuming one value in a multi-value field.")
        return self._raw_values[0]


class ExifHeader():
# class ExifHeader(collections.MutableMapping, object):
    """Class that handles an EXIF header"""

    def __init__(self, file_obj, endian, offset, fake_exif=False, strict=False,
                 detailed=True, debug=False):
        self.file = file_obj
        self.endian = endian
        self.offset = offset
        self.fake_exif = fake_exif
        self.strict = strict
        self.detailed = detailed
        self.debug = debug

    def __iter__(self):
        for i in self.tags:
            yield i

    def __getitem__(self, item):
        return str(self.tags[item])

    def __setitem__(self, key, value):
        raise RuntimeError("ExifHeader object is read-only")

    def __delitem__(self, key):
        raise RuntimeError("ExifHeader object is read-only")

    def itervalues(self):
        return self.tags.itervalues()

    @lazy_property
    def tags(self):
        logger.debug('Running tags extraction')

        tags = {}
        ctr = 0
        thumb_ifd = None

        for i in self._list_ifds():
            if ctr == 0:
                ifd_name = 'Image'

            elif ctr == 1:
                ifd_name = 'Thumbnail'
                thumb_ifd = i

            else:
                ifd_name = 'IFD {}'.format(ctr)

            logger.debug('IFD {:d} ({}) at offset {:d}:'
                         ''.format(ctr, ifd_name, i))

            self._extract_tags(tags, ifd=i, ifd_name=ifd_name)

            # # EXIF IFD
            exif_offset = tags.get('{} ExifOffset'.format(ifd_name))
            if exif_offset:
                logger.debug(
                    'EXIF SubIFD at offset {:d}:'.format(exif_offset.value))
                self._extract_tags(
                    tags=tags,
                    ifd=exif_offset.value,
                    ifd_name='EXIF')

                # Interoperability IFD contained in EXIF IFD
                intr_offset = tags.get('EXIF SubIFD InteroperabilityOffset')
                if intr_offset:
                    logger.debug(
                        'EXIF Interoperability SubSubIFD at offset {:d}:'
                        ''.format(intr_offset.value))
                    self._extract_tags(
                        tags=tags,
                        ifd=intr_offset.value,
                        ifd_name='EXIF Interoperability',
                        tags_library=INTR_TAGS)

            # # GPS IFD
            gps_offset = tags.get('{} GPSInfo'.format(ifd_name))
            if gps_offset:
                logger.debug('GPS SubIFD at offset {:d}:'
                             ''.format(gps_offset.value))
                self._extract_tags(
                    tags=tags,
                    ifd=gps_offset.value,
                    ifd_name='GPS',
                    tags_library=GPS_TAGS)
            ctr += 1

        # # Extract uncompressed TIFF thumbnail
        thumb = tags.get('Thumbnail Compression')
        if thumb_ifd is not None \
                and thumb \
                and thumb.printable == 'Uncompressed TIFF':
            self._extract_tiff_thumbnail(tags, thumb_ifd)

        # # JPEG thumbnail (thankfully the JPEG data is stored as a unit)
        thumb_off = tags.get('Thumbnail JPEGInterchangeFormat')
        if thumb_off:
            self.file.seek(self.offset + thumb_off.value)
            size = tags['Thumbnail JPEGInterchangeFormatLength'].value
            tags['JPEGThumbnail'] = self.file.read(size)

        # # Deal with MakerNote contained in EXIF IFD
        # # (Some apps use MakerNote tags but do not use a format for which we
        # # have a description, do not process these).
        if self.detailed and \
                ('EXIF MakerNote' in tags) and \
                ('Image Make' in tags):
            self._decode_maker_note(tags)

        # # Sometimes in a TIFF file, a JPEG thumbnail is hidden in the MakerNote
        # # since it's not allowed in a uncompressed TIFF IFD
        if 'JPEGThumbnail' not in tags:
            thumb_off = tags.get('MakerNote JPEGThumbnail')
            if thumb_off:
                self.file.seek(self.offset + thumb_off.value)
                tags['JPEGThumbnail'] = file.read(thumb_off.field_length)

        return tags

    def _read_int(self, offset, length, signed=False):
        """
        Reads ``length`` characters from the relative offset ``offset``.
        Converts the number to integer depending on found endianness.

        Convert slice to integer, based on sign and endian flags
        Usually this offset is assumed to be relative to the beginning of the
        start of the EXIF information.
        For some cameras that use relative tags, this offset may be relative
        to some other starting point.
        """
        self.file.seek(self.offset + offset)
        chunk = self.file.read(length)
        if self.endian == 'I':
            return unpack_intel(chunk, signed=signed)
        else:
            return unpack_motorola(chunk, signed=signed)

    def _encode_int(self, number, length):
        """
        Convert an int to its binary representation, considering endianness
        """
        if self.endian == 'I':
            return pack_intel(number, length=length)
        else:
            return pack_motorola(number, length=length)

    def _first_ifd(self):
        """Return first IFD"""
        return self._read_int(4, 4)

    def _next_ifd(self, ifd):
        """Return pointer to next IFD, afther the specified one"""
        entries = self._read_int(ifd, 2)
        next_ifd = self._read_int(ifd + 2 + 12 * entries, 4)
        if next_ifd == ifd:
            return 0
        else:
            return next_ifd

    def _list_ifds(self):
        """Return list of IFDs in header"""
        # todo: refactor this..
        i = self._first_ifd()
        while i:
            yield i
            i = self._next_ifd(i)

    def _extract_tags(self, tags, ifd, ifd_name, tags_library=None, relative=0):
        """Extract IFD tags and add to tags

        :param tags: Dictionary of extracted tags
        :param ifd: The initial offset from which we start reading
        :param ifd_name:
        :param tags_library: EXIF tags database
        :param relative:
        """

        if tags_library is None:
            tags_library = EXIF_TAGS

        # # The number of tags we expect to read
        entries_count = self._read_int(ifd, 2)

        for i in xrange(entries_count):
            # # Entry is index of start of this IFD in the file
            entry = ifd + 2 + (12 * i)
            tag = self._read_int(entry, 2)

            # # Get tag name early to avoid errors, help debug
            tag_entry = tags_library.get(tag)
            if tag_entry:
                tag_name = tag_entry[0]
            else:
                tag_name = 'Tag 0x{:04X}'.format(tag)

            # # ignore certain tags for faster processing
            # if not (not self.detailed and tag in IGNORE_TAGS):  # <-- WTF?
            if self.detailed or tag not in IGNORE_TAGS:
                field_type = self._read_int(entry + 2, 2)

                if field_type not in FIELD_TYPES:
                    # # We found an unknown field type
                    message = 'Unknown type {:d} in tag 0x{:04X}' \
                              ''.format(field_type, tag)
                    if self.strict:
                        raise ValueError(message)
                    else:
                        warnings.warn(message)
                        continue  # Just skip

                # # Get the field length for this type
                type_len = FIELD_TYPES[field_type][0]

                # # Amount of values for this field
                values_count = self._read_int(entry + 4, 4)

                # # Adjust for tag id/type/value_count (2+2+4 bytes)
                # # Now we point at either the data or the 2nd level offset
                offset = entry + 8

                # # If the value fits in 4 bytes, it is inlined, else we
                # # need to jump ahead again.
                if (values_count * type_len) > 4:
                    # # offset is not the value; it's a pointer to the value
                    # # if relative we set things up so s2n will seek to the
                    # # right place when it adds self.offset.
                    # # Note that this 'relative' is for the Nikon type 3
                    # # makernote.
                    # # Other cameras may use other relative offsets, which
                    # # would have to be computed here slightly differently.
                    if relative:
                        tmp_offset = self._read_int(offset, 4)
                        offset = tmp_offset + ifd - 8
                        if self.fake_exif:
                            offset += 18
                    else:
                        offset = self._read_int(offset, 4)

                field_offset = offset
                values = None

                if field_type == FT_ASCII:
                    # # Special case: null-terminated ASCII string
                    # # todo: investigate
                    # # Sometimes gets too big to fit in int value (in Python??)

                    if values_count > 0:
                        # # Was: and value_count < (2**31):
                        # # but 2E31 is hardware dependant. --gd
                        try:
                            self.file.seek(self.offset + offset)
                            values = self.file.read(values_count)
                            # # Drop any garbage after a null.
                            try:
                                zeroidx = values.index('\x00')
                            except ValueError:  # No zero in values
                                pass
                            else:
                                values = values[:zeroidx]
                            values = [values]  # Must be a list..

                        except OverflowError:  # Why??
                            values = []

                else:
                    signed_types = (
                        FT_SIGNED_BYTE,
                        FT_SIGNED_SHORT,
                        FT_SIGNED_LONG,
                        FT_SIGNED_RATIO,
                    )
                    values = []
                    signed = (field_type in signed_types)

                    if values_count > 1000:
                        # # todo: investigate this:
                        # # some entries get too big to handle could be malformed
                        # # file or problem with self.s2n
                        # values_count = 1000
                        if tag_name != 'MakerNote':
                            warnings.warn(
                                "Encountered tag {} with > 1000 values "
                                "({} found). Limiting to 1000."
                                "".format(tag_name, values_count))
                            values_count = 1000

                    for dummy in xrange(values_count):
                        if field_type in (FT_RATIO, FT_SIGNED_RATIO):
                            # # This is a ratio
                            value = Ratio(
                                self._read_int(offset, 4, signed),
                                self._read_int(offset + 4, 4, signed))
                        else:
                            # # This is an int
                            value = self._read_int(offset, type_len, signed)

                        values.append(value)
                        offset += type_len


                # ## Now 'values' is either a string or an array
                # ## todo: WTF???
                # if value_count == 1 and field_type != FT_ASCII:
                #     printable = str(values[0])
                #
                # elif value_count > 50 and len(values) > 20:
                #     printable = str(values[0:20])[0:-1] + ", ... ]"
                #
                # else:
                #     printable = str(values)
                #
                # ## Compute printable version of values
                # ## todo: this should be generated by the tag at need...
                # if tag_entry:
                #     if len(tag_entry) != 1:
                #         # optional 2nd tag element is present
                #         if callable(tag_entry[1]):
                #             # call mapping function
                #             printable = tag_entry[1](values)
                #         else:
                #             printable = ''
                #             for i in values:
                #                 # use lookup table for this tag
                #                 printable += tag_entry[1].get(i, repr(i))

                _tag_name = '{} {}'.format(ifd_name, tag_name)

                new_tag = IFD_Tag(
                    tag=tag,
                    field_type=field_type,
                    values=values,
                    field_offset=field_offset,
                    field_length=values_count * type_len,
                    tag_entry=tag_entry)

                logger.debug('Added tag: {}: {!r}'.format(tag_name, new_tag))

                tags[_tag_name] = new_tag

    def _extract_tiff_thumbnail(self, tags, thumb_ifd):
        """
        Extract uncompressed TIFF thumbnail (like pulling teeth)
        We take advantage of the pre-existing layout in the thumbnail IFD as
        much as possible
        """
        entries = self._read_int(thumb_ifd, 2)
        # this is header plus offset to IFD ...
        if self.endian == 'M':
            tiff = 'MM\x00*\x00\x00\x00\x08'
        else:
            tiff = 'II*\x00\x08\x00\x00\x00'
            # ... plus thumbnail IFD data plus a null "next IFD" pointer
        self.file.seek(self.offset + thumb_ifd)
        tiff += self.file.read(entries * 12 + 2) + '\x00\x00\x00\x00'

        # fix up large value offset pointers into data area

        strip_off = None  # todo: handle this properly!!

        for i in range(entries):
            entry = thumb_ifd + 2 + 12 * i
            tag = self._read_int(entry, 2)
            field_type = self._read_int(entry + 2, 2)
            typelen = FIELD_TYPES[field_type][0]
            count = self._read_int(entry + 4, 4)
            oldoff = self._read_int(entry + 8, 4)
            # start of the 4-byte pointer area in entry
            ptr = i * 12 + 18
            # remember strip offsets location
            if tag == 0x0111:
                strip_off = ptr
                strip_len = count * typelen
                # is it in the data area?
            if count * typelen > 4:
                # update offset pointer (nasty "strings are immutable" crap)
                # should be able to say "tiff[ptr:ptr+4]=newoff"
                newoff = len(tiff)

                # tiff = tiff[:ptr] + self.n2s(newoff, 4) + tiff[ptr + 4:]
                tiff = ''.join((
                    tiff[:ptr],
                    self._encode_int(newoff, 4),
                    tiff[ptr + 4:]
                ))

                # remember strip offsets location
                if tag == 0x0111:
                    strip_off = newoff
                    strip_len = 4
                    # get original data and store it
                self.file.seek(self.offset + oldoff)
                tiff += self.file.read(count * typelen)

        # add pixel strips and update strip offset info
        old_offsets = tags['Thumbnail StripOffsets'].values
        old_counts = tags['Thumbnail StripByteCounts'].values
        for i in range(len(old_offsets)):
            # update offset pointer (more nasty "strings are immutable" crap)
            offset = self._encode_int(len(tiff), strip_len)
            # tiff = tiff[:strip_off] + offset + tiff[strip_off + strip_len:]
            tiff = ''.join((
                tiff[:strip_off],
                offset,
                tiff[strip_off + strip_len:]
            ))
            strip_off += strip_len
            # add pixel strip to end
            self.file.seek(self.offset + old_offsets[i])
            tiff += self.file.read(old_counts[i])

        tags['TIFFThumbnail'] = tiff

    def _decode_maker_note(self, tags):
        """
        Decode all the camera-specific MakerNote formats

        Note is the data that comprises this MakerNote.  The MakerNote will
        likely have pointers in it that point to other parts of the file.
        We'll use self.offset as the starting point for most of those pointers,
        since they are relative to the beginning of the file.

        If the MakerNote is in a newer format, it may use relative addressing
        within the MakerNote.  In that case we'll use relative addresses
        for the pointers.

        As an aside: it's not just to be annoying that the manufacturers use
        relative offsets.  It's so that if the makernote has to be moved by
        the picture software all of the offsets don't have to be adjusted.
        Overall, this is probably the right strategy for makernotes, though
        the spec is ambiguous.

        (The spec does not appear to imagine that makernotes would follow
        EXIF format internally. Once they did, it's ambiguous whether the
        offsets should be from the header at the start of all the EXIF info,
        or from the header at the start of the makernote.)
        """

        note = tags['EXIF MakerNote']

        # # Some apps use MakerNote tags but do not use a format for which we
        # # have a description, so just do a raw dump for these.
        make = tags['Image Make'].value

        # model = tags['Image Model'].printable # unused

        # # Nikon
        # # The maker note usually starts with the word Nikon, followed by the
        # # type of the makernote (1 or 2, as a short).  If the word Nikon is
        # # not at the start of the makernote, it's probably type 2, since some
        # # cameras work that way.
        if 'NIKON' in make:
            if note.values[0:7] == [78, 105, 107, 111, 110, 0, 1]:
                logger.debug("Looks like a type 1 Nikon MakerNote.")
                self._extract_tags(tags, note.field_offset + 8, 'MakerNote',
                                   tags_library=MAKERNOTE_NIKON_OLDER_TAGS)
            elif note.values[0:7] == [78, 105, 107, 111, 110, 0, 2]:
                logger.debug("Looks like a labeled type 2 Nikon MakerNote")
                _nv_12t14 = note.values[12:14]
                if _nv_12t14 != [0, 42] and _nv_12t14 != [42, 0]:
                    raise ValueError("Missing marker tag '42' in MakerNote.")
                    # # Skip the Makernote label and the TIFF header
                self._extract_tags(tags, note.field_offset + 10 + 8,
                                   'MakerNote',
                                   tags_library=MAKERNOTE_NIKON_NEWER_TAGS,
                                   relative=1)
            else:
                # E99x or D1
                logger.debug("Looks like an unlabeled type 2 Nikon MakerNote")
                self._extract_tags(tags, note.field_offset, 'MakerNote',
                                   tags_library=MAKERNOTE_NIKON_NEWER_TAGS)
            return

        # # Olympus
        if make.startswith('OLYMPUS'):
            self._extract_tags(tags, note.field_offset + 8, 'MakerNote',
                               tags_library=MAKERNOTE_OLYMPUS_TAGS)
            # XXX TODO
            # for i in (('MakerNote Tag 0x2020', MAKERNOTE_OLYMPUS_TAG_0x2020),):
            #    self.decode_olympus_tag(tags[i[0]].values, i[1])
            # return

        # # Casio
        if 'CASIO' in make or 'Casio' in make:
            self._extract_tags(tags, note.field_offset, 'MakerNote',
                               tags_library=MAKERNOTE_CASIO_TAGS)
            return

        # # Fujifilm
        if make == 'FUJIFILM':
            # bug: everything else is "Motorola" endian, but the MakerNote
            # is "Intel" endian
            endian = self.endian
            self.endian = 'I'
            # bug: IFD offsets are from beginning of MakerNote, not
            # beginning of file header
            offset = self.offset
            self.offset += note.field_offset
            # process note with bogus values (note is actually at offset 12)
            self._extract_tags(tags, 12, 'MakerNote',
                               tags_library=MAKERNOTE_FUJIFILM_TAGS)
            # reset to correct values
            self.endian = endian
            self.offset = offset
            return

        # # Canon
        if make == 'Canon':
            self._extract_tags(tags, note.field_offset, 'MakerNote',
                               tags_library=MAKERNOTE_CANON_TAGS)
            for i in (('MakerNote Tag 0x0001', MAKERNOTE_CANON_TAG_0x001),
                      ('MakerNote Tag 0x0004', MAKERNOTE_CANON_TAG_0x004)):
                if i[0] in tags:
                    self._decode_canon_tag(tags, tags[i[0]].values, i[1])
            return

    # XXX TODO decode Olympus MakerNote tag based on offset within tag
    def _decode_olympus_tag(self, value, context):
        pass

    # decode Canon MakerNote tag based on offset within tag
    # see http://www.burren.cx/david/canon.html by David Burren
    def _decode_canon_tag(self, tags, value, context):
        for i in range(1, len(value)):
            x = context.get(i, ('Unknown',))
            logger.debug('{!r} {!r}'.format(i, x))
            name = x[0]
            if len(x) > 1:
                val = x[1].get(value[i], 'Unknown')
            else:
                val = value[i]
                # it's not a real IFD Tag but we fake one to make everybody
            # happy. this will have a "proprietary" type
            tags['MakerNote {}'.format(name)] = \
                IFD_Tag(values=[str(val)], tag=None, field_type=0)