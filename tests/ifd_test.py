from rawphoto.cr2 import Ifd

import os
import pytest

ifd_bytes = b'''\
\x02\x00\x01\x02\x04\x00\x01\x00\x00\x00\x08\xd7\x00\x00\x02\x02\x04\x00\x01\x00\x00\x00P-\x00\x00\xee\xb5\x00\x00
'''


def test_ifd_must_have_single_data_source():
    with pytest.raises(TypeError):
        Ifd("<", blob=1, file=1, offset=1)


def test_new_ifd_from_file(tmpdir):
    p = tmpdir.realpath().strpath
    with open(os.path.join(p, 'ifd'), mode='w+b') as tmpfile:
        tmpfile.write(ifd_bytes)
        tmpfile.seek(0)
        ifd = Ifd("<", file=tmpfile)
        assert len(ifd.entries) == 2


def test_new_ifd_from_blob():
    ifd = Ifd("<", blob=ifd_bytes)
    assert len(ifd.entries) == 2
    assert 'thumbnail_offset' in ifd.entries
    assert 'thumbnail_length' in ifd.entries


def test_new_ifd_from_blob_with_offset():
    ifd = Ifd("<", blob=b'\x00' + ifd_bytes, offset=1)
    assert len(ifd.entries) == 2


# TODO: Add test for sub-ifd parsing.

def test_get_value_invalid_offset():
    ifd = Ifd("<", blob=ifd_bytes)
    assert len(ifd.entries) == 2
    assert ifd.get_value(ifd.entries['thumbnail_offset']) == \
        ifd.entries['thumbnail_offset'].raw_value
    assert ifd.get_value(ifd.entries['thumbnail_length']) == \
        ifd.entries['thumbnail_length'].raw_value

# TODO: Add test of reading string and byte array
# TODO: Add test of reading decimal or other value with indirect
# TODO: Add test of reading in-place value
