"""
Definition of field types
"""

__all__ = ['FIELD_TYPES',
           'FT_PROPRIETARY', 'FT_BYTE', 'FT_ASCII', 'FT_LONG', 'FT_RATIO',
           'FT_SHORT', 'FT_SIGNED_BYTE', 'FT_SIGNED_LONG', 'FT_SIGNED_RATIO',
           'FT_SIGNED_SHORT', 'FT_UNDEFINED']


FT_PROPRIETARY = 0
FT_BYTE = 1
FT_ASCII = 2
FT_SHORT = 3
FT_LONG = 4
FT_RATIO = 5
FT_SIGNED_BYTE = 6
FT_UNDEFINED = 7
FT_SIGNED_SHORT = 8
FT_SIGNED_LONG = 9
FT_SIGNED_RATIO = 10


def _dummy(x):
    return x


def _ratio(x):
    from py3exif.objects import Ratio
    return Ratio(x)


FIELD_TYPES = {
    # (typelen, ?, description, decoder)
    FT_PROPRIETARY: (0, 'X', 'Proprietary', _dummy),  # no such type
    FT_BYTE: (1, 'B', 'Byte', _dummy),
    FT_ASCII: (1, 'A', 'ASCII', _dummy),
    FT_SHORT: (2, 'S', 'Short', int),
    FT_LONG: (4, 'L', 'Long', int),
    FT_RATIO: (8, 'R', 'Ratio', _ratio),
    FT_SIGNED_BYTE: (1, 'SB', 'Signed Byte', _dummy),
    FT_UNDEFINED: (1, 'U', 'Undefined', _dummy),
    FT_SIGNED_SHORT: (2, 'SS', 'Signed Short', int),
    FT_SIGNED_LONG: (4, 'SL', 'Signed Long', int),
    FT_SIGNED_RATIO: (8, 'SR', 'Signed Ratio', _ratio),
}
