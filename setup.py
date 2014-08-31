#!/usr/bin/env python3

from setuptools import setup, find_packages
from py3exif.version import __version__

classifiers = [
    # # todo: add classifiers..
    "Programming Language :: Python",
]

entry_points = {
    'console_scripts': [
        'py3exif = py3exif.__main__:main',
    ],
}

setup(
    name='py3exif',
    version=__version__,
    description='EXIF library for Python 2.7',
    long_description='Library for Python 2.7 to extract EXIF data from TIFF and JPEG files.',
    author='',
    author_email='',
    license='',
    url='',
    classifiers=classifiers,
    entry_points=entry_points,
    # install_requires=[],
    packages=find_packages(),
    # include_package_data=True,
    # zip_safe=False,
    test_suite='tests',
)
