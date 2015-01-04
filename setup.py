from setuptools import setup

setup(
    name='rawphoto',
    version='0.0.0',
    description='Utilities for managing raw photos',
    author='Sam Whited',
    author_email='sam@samwhited.com',
    url='https://github.com/photoshell/rawphoto',
    packages=['rawphoto'],
    keywords=['encoding', 'images', 'cr2'],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Environment :: Other Environment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    long_description="""\
Raw image file parser
---------------------

Currently supports
  - Canon CR2

This version has only been tested with Python 3.4.
"""

)
