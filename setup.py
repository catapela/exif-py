#!/usr/bin/env python

from setuptools import setup, find_packages
from exifpy.version import __version__

classifiers = [
    ## todo: add classifiers..
    "Programming Language :: Python",
]

entry_points = {
    'console_scripts': [
        'exifpy = exifpy.__main__:main',
    ],
}

setup(
    name='ExifPy',
    version=__version__,
    description='',
    long_description='',
    author='',
    author_email='',
    license='',
    url='',
    classifiers=classifiers,
    entry_points=entry_points,
    #install_requires=[],
    packages=find_packages(),
    #include_package_data=True,
    #zip_safe=False,
)
