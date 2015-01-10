from rawphoto.cr2 import IfdEntry

import os
import pytest

ifd_entry = b'\x0f\x01\x02\x00\x06\x00\x00\x00\xe8\x00\x00\x00'
ifd_entry_not_offset = b'@\xc6\x03\x00\x03\x00\x00\x00\x00\xb7\x00\x00'
unknown_tag_ifd_entry = b'\xc5\xc6\x04\x00\x01\x00\x00\x00\x01\x00\x00\x00'


def test_ifd_entry_must_have_single_data_source():
    with pytest.raises(TypeError):
        IfdEntry("<", blob=1, file=1, offset=1)


def test_new_ifd_entry_from_file(tmpdir):
    p = tmpdir.realpath().strpath
    with open(os.path.join(p, 'ifd_entry'), mode='w+b') as tmpfile:
        tmpfile.write(ifd_entry)
        tmpfile.seek(0)
        entry = IfdEntry("<", file=tmpfile)
    assert entry.tag_id == 271
    assert entry.tag_name == 'make'
    assert entry.tag_type == 's'
    assert entry.value_len == 6
    assert entry.raw_value == 232


def test_new_ifd_entry_from_blob():
    entry = IfdEntry("<", blob=ifd_entry)
    assert entry.tag_id == 271
    assert entry.tag_name == 'make'
    assert entry.tag_type == 's'
    assert entry.value_len == 6
    assert entry.raw_value == 232


def test_new_ifd_entry_from_blob_with_offset():
    entry = IfdEntry("<", blob=(b'\x00' + ifd_entry), offset=1)
    assert entry.tag_id == 271
    assert entry.tag_name == 'make'
    assert entry.tag_type == 's'
    assert entry.value_len == 6
    assert entry.raw_value == 232


def test_unknown_tag_name_should_be_id():
    entry = IfdEntry("<", blob=unknown_tag_ifd_entry)
    assert entry.tag_name == 50885


def test_raw_value_not_offset():
    entry = IfdEntry("<", blob=ifd_entry_not_offset)
    assert entry.raw_value == 46848
