from rawphoto.cr2 import Cr2
from tests.cr2_header_test import header_bytes
from tests.ifd_test import ifd_bytes
from tests.ifd_test import ifd_bytes_string_value
from io import BytesIO

import os
import pytest
import struct

# TODO: Convert these to fixtures.
cr2_bytes = header_bytes + ifd_bytes
ifd_strip_image = b'''\
\x02\x00\x11\x01\x04\x00\x01\x00\x00\x00\x00\x00\x00\x00\x17\x01\x04\x00\x01\
\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\
'''

cr2_multiple_ifds = cr2_bytes[0:-4] + struct.pack(
    '<L', len(cr2_bytes)) + ifd_bytes_string_value
cr2_multiple_ifds = cr2_multiple_ifds[0:-10] + struct.pack(
    '<L', len(cr2_multiple_ifds)) + b'Canon\x00' + ifd_strip_image
cr2_multiple_ifds = cr2_multiple_ifds[0:-4] + struct.pack(
    '<L', len(cr2_multiple_ifds)) + ifd_strip_image

cr2_thumbnail = cr2_bytes[0:-4] + struct.pack(
    '<L', len(cr2_bytes)) + ifd_bytes


def test_cr2_must_have_single_data_source():
    with pytest.raises(TypeError):
        Cr2()
    with pytest.raises(TypeError):
        Cr2(offset=1)
    with pytest.raises(TypeError):
        Cr2(blob=1, file=1)
    with pytest.raises(TypeError):
        Cr2(blob=1, filename=1)
    with pytest.raises(TypeError):
        Cr2(file=1, filename=1)


def test_file(tmpdir):
    p = os.path.join(tmpdir.realpath().strpath, 'cr2.CR2')
    with open(p, mode='w+b') as tmpfile:
        tmpfile.write(cr2_bytes)
        tmpfile.seek(0)
        cr2 = Cr2(file=tmpfile)
        assert cr2.fhandle == tmpfile


def test_blob():
    with Cr2(blob=cr2_bytes) as cr2:
        assert isinstance(cr2.fhandle, BytesIO)


def test_filename(tmpdir):
    p = os.path.join(tmpdir.realpath().strpath, 'cr2.CR2')
    with open(p, mode='w+b') as tmpfile:
        tmpfile.write(header_bytes)
        tmpfile.write(ifd_bytes)
    with Cr2(filename=p) as cr2:
        assert cr2.fhandle.name == p


def test_reads_all_ifds():
    with Cr2(blob=cr2_multiple_ifds) as cr2:
        assert len(cr2.ifds) == 4


def test_read_seek_close_cr2():
    cr2 = Cr2(blob=cr2_bytes)
    cr2.seek(0)
    data = cr2.read()
    cr2.fhandle.seek(0)
    data2 = cr2.read()
    cr2.fhandle.close()

    assert data == data2
    assert cr2.fhandle.closed


def test_fetching_thumbnail_ifd_index_error():
    with Cr2(blob=cr2_bytes) as cr2:
        with pytest.raises(IndexError):
            cr2.thumbnail_image


def test_fetching_thumbnail():
    with Cr2(blob=cr2_thumbnail) as cr2:
        assert cr2.thumbnail_image == b'II'


def test_fetching_thumbnail_no_exists():
    with Cr2(blob=cr2_multiple_ifds) as cr2:
        assert cr2.thumbnail_image is None


def test_fetch_uncompressed_rgb_no_white_balance():
    with Cr2(blob=cr2_multiple_ifds) as cr2:
        assert cr2.uncompressed_full_size_image == b'II'


def test_get_raw_data():
    with Cr2(blob=cr2_multiple_ifds) as cr2:
        assert cr2.raw_data == b'II'
