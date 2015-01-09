from rawphoto.cr2 import IfdEntry

import pytest

ifd_entry_bytes = b'\x0f\x01\x02\x00\x06\x00\x00\x00\xe8\x00\x00\x00'


def test_ifd_must_have_single_data_source():
    with pytest.raises(TypeError):
        IfdEntry("<", blob=1, file=1, offset=1)


def test_new_ifd_entry_from_blob():
    entry = IfdEntry("<", blob=ifd_entry_bytes)
    assert entry.tag_id == 271
    assert entry.tag_name == 'make'
    assert entry.tag_type == 's'
    assert entry.value_len == 6
    assert entry.raw_value == 232


def test_new_ifd_entry_from_blob_with_offset():
    entry = IfdEntry("<", blob=(b'\x00' + ifd_entry_bytes), offset=1)
    assert entry.tag_id == 271
    assert entry.tag_name == 'make'
    assert entry.tag_type == 's'
    assert entry.value_len == 6
    assert entry.raw_value == 232
