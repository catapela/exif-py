"""
ExifPy Exceptions
"""


class ExifPyGoodException(Exception):
    """
    Exception due to missing data to extract, these doesn't
    (usually) mean there was a problem with the library.
    """
    pass


class UnsupportedFormat(ExifPyGoodException):
    """
    Unsupported file format: not a jpeg/tiff
    """
    pass


class NoExifData(ExifPyGoodException):
    """
    No EXIF data found in the image
    """
    pass


class ExifPyBadException(Exception):
    """
    Exception due to a problem with parsing -- this might
    indicate there is a problem with the parser somewhere..
    """
    pass
