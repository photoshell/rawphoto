from setuptools import setup

setup(
    name='rawphoto',
    version='0.2.0',
    description='Utilities for managing raw photos',
    author='Sam Whited',
    author_email='sam@samwhited.com',
    url='https://github.com/photoshell/rawphoto',
    packages=['rawphoto'],
    keywords=['encoding', 'images', 'photography'],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Development Status :: 3 - Alpha",
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
"""

)
