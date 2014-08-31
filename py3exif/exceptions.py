"""
py3exif Exceptions
"""


class py3exifGoodException(Exception):
    """
    Exception due to missing data to extract, these doesn't
    (usually) mean there was a problem with the library.
    """
    pass


class UnsupportedFormat(py3exifGoodException):
    """
    Unsupported file format: not a jpeg/tiff
    """
    pass


class NoExifData(py3exifGoodException):
    """
    No EXIF data found in the image
    """
    pass


class py3exifBadException(Exception):
    """
    Exception due to a problem with parsing -- this might
    indicate there is a problem with the parser somewhere..
    """
    pass
