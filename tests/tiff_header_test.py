import pytest

from rawphoto.tiff import Header

header_bytes = b'II*\x00\x10\x00\x00\x00'
header_bytes_read = (18761, 42, 16)


# New headers should decode bytes properly
def test_new_header():
    header = Header(header_bytes)
    assert header.raw_header == header_bytes_read
    assert header.endianness == '<'
    assert header.tiff_magic_word == 42
    assert header.first_ifd_offset == 16


# Invalid header should raise `TypeError'
def test_invalid_header():
    with pytest.raises(TypeError):
        Header(1)
