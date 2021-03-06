# Description

**Version:** 1.2.2

library for Python 2.7 (python3 not supported yet) to extract EXIF data from tiff and jpeg files.

Exif.py was originally written by Gene Cash / Thierry Bousch.


## Installation

From the source code directory, run:

    $ setup.py install

Or, to install directly from git:

    $ pip install git+git://github.com/catapela/exif-py.git


## Command line Usage

    $ py3exif image.jpg

Show command line options:

    $ py3exif --help


## Python Script Usage

```python
import py3exif

# Open image file for reading (binary mode)
f = open(path_name, 'rb')

# Return Exif tags
tags = py3exif.process_file(f)
```

Returned tags will be a dictionary mapping names of Exif tags to their
values in the file named by path_name.

You can process the tags as you wish. In particular, you can iterate through
all the tags with:

```python
for tag in tags:
    if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):
        print("Key: %s, value %s" % (tag, tags[tag]))
```

An if statement is used to avoid printing out a few of the tags that tend
to be long or boring.

The tags dictionary will include keys for all of the usual Exif tags,
and will also include keys for Makernotes used by some cameras, for which
we have a good specification.

Note that the dictionary keys are the IFD name followed by the tag name.
For example:

`'EXIF DateTimeOriginal', 'Image Orientation', 'MakerNote FocusMode'`


## Processing Options

These options can be used both in command line mode and within a script.

#### Ignore MakerNote Tags

Pass the `-q` or `--quick` command line arguments, or as

```python
tags = EXIF.process_file(f, detailed=False)
```

#### Strict Processing

Return an error on invalid tags instead of silently ignoring.

Pass the `-s` or `--strict` argument, or as

```python
tags = EXIF.process_file(f, strict=True)
```
