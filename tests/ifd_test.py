from rawphoto.tiff import Ifd

import os
import pytest

ifd_bytes = b'''\
\x02\x00\x01\x02\x04\x00\x01\x00\x00\x00\x00\x00\x00\x00\x02\x02\x04\x00\x01\
\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\
'''

ifd_bytes_sub_ifd = b'''\
\x01\x00i\x87\x04\x00\x01\x00\x00\x00\x12\x00\x00\x00\x12\x00\x00\x00\
\x01\x00\x01\x02\x04\x00\x01\x00\x00\x00\x08\xd7\x00\x00\x00\x00\x00\x00\
'''

ifd_bytes_string_value = b'''\
\x01\x00\
\x0f\x01\x02\x00\x06\x00\x00\x00\x12\x00\x00\x00\
\x00\x00\x00\x00Canon\x00\
'''

ifd_bytes_byte_array = b'''\
\x01\x00\
\x0f\x01\x07\x00\x06\x00\x00\x00\x12\x00\x00\x00\
\x00\x00\x00\x00Canon\x00\
'''

ifd_bytes_double = b'''\
\x01\x00\
\x0f\x01\x0c\x00\x01\x00\x00\x00\x12\x00\x00\x00\
\x00\x00\x00\x00\x1f\x85\xebQ\xb8\x1e\t@\
'''

ifd_bytes_float = b'''\
\x01\x00\
\x0f\x01\x0b\x00\x01\x00\x00\x00)\\\xcf?\
\x00\x00\x00\x00\
'''

ifd_bytes_invalid_pointer = b'''\
\x01\x00\x0f\x01\x0c\x00\x06\x00\x00\x00\x12\x12\x12\x12\x00\x00\x00\x00\
'''


def test_ifd_must_have_single_data_source():
    with pytest.raises(TypeError):
        Ifd("<")
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
    assert 'data_offset' in ifd.entries
    assert 'data_length' in ifd.entries


def test_new_ifd_from_blob_with_offset():
    ifd = Ifd("<", blob=b'\x00' + ifd_bytes, offset=1)
    assert len(ifd.entries) == 2


def test_ifds_must_parse_sub_ifds():
    ifd = Ifd("<", blob=ifd_bytes_sub_ifd, subdirs=[0x8769])
    assert 'exif' in ifd.entries
    assert len(ifd.subifds) == 1
    assert 'exif' in ifd.subifds
    assert 'data_offset' in ifd.subifds['exif'].entries


def test_get_value_invalid_offset():
    ifd = Ifd("<", blob=ifd_bytes)
    assert len(ifd.entries) == 2
    assert ifd.get_value(ifd.entries['data_offset']) == \
        ifd.entries['data_offset'].raw_value
    assert ifd.get_value(ifd.entries['data_length']) == \
        ifd.entries['data_length'].raw_value


def test_ifd_get_string_value():
    ifd = Ifd("<", blob=ifd_bytes_string_value)
    val = ifd.get_value(ifd.entries['make'])
    assert isinstance(val, (type(u""), str))
    assert val == 'Canon'


def test_ifd_get_byte_array_value():
    ifd = Ifd("<", blob=ifd_bytes_byte_array)
    val = ifd.get_value(ifd.entries['make'])
    assert isinstance(val, bytes)
    assert val == b'Canon\x00'


def test_ifd_get_double():
    ifd = Ifd("<", blob=ifd_bytes_double)
    val = ifd.get_value(ifd.entries['make'])
    assert round(val - 3.14, 2) == 0


def test_ifd_get_float():
    ifd = Ifd("<", blob=ifd_bytes_float)
    val = ifd.get_value(ifd.entries['make'])
    assert round(val - 1.62, 2) == 0


def test_ifd_invalid_pointer():
    ifd = Ifd("<", blob=ifd_bytes_invalid_pointer)
    val = ifd.get_value(ifd.entries['make'])
    assert val == 303174162
