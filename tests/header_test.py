import pytest

from rawphoto.cr2 import Header

header_bytes = b'II*\x00\x10\x00\x00\x00CR\x02\x00F\xbf\x00\x00'
header_bytes_read = (18761, 42, 16, 21059, 2, 0, 48966)


# New headers should decode bytes properly
def test_new_header():
    header = Header(header_bytes)
    assert header.raw_header == header_bytes_read
    assert header.endianness == '<'
    assert header.tiff_magic_word == 42
    assert header.tiff_offset == 16
    assert header.magic_word == 21059
    assert header.major_version == 2
    assert header.minor_version == 0
    assert header.raw_ifd_offset == 48966


# Invalid header should raise `TypeError'
def test_invalid_header():
    with pytest.raises(TypeError):
        Header(1)
