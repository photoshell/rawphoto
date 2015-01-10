# Contributing

[![Build Status](https://travis-ci.org/SamWhited/rawphoto.svg)](https://travis-ci.org/SamWhited/rawphoto)
[![Coverage Status](https://img.shields.io/coveralls/SamWhited/rawphoto.svg)](https://coveralls.io/r/SamWhited/rawphoto)

The source for **rawphoto** can be found on [GitHub][source]. Or simply:

    git clone git://github.com/photoshell/rawphoto

All code must follow PEP8 standards. Before doing anything, be sure to install
and configure [pre-commit][precommit]. If your code doesn't pass our pre-commit
tests, it won't be merged. It should also have full test coverage (unless large
ammounts of data are required for the test), and build (obviously).

Finally, your code should be compatible with both Python 2 and 3 (see `tox.ini`
for the versions we actually test against; needless to say, the entire test
matrix should pass).

[source]: https://github.com/photoshell/rawphoto
[precommit]: http://pre-commit.com/
