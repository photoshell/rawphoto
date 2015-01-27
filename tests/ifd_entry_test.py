from io import BytesIO
from rawphoto.tiff import IfdEntry
from rawphoto.cr2 import tags

import os
import pytest


@pytest.fixture
def ifd_entry():
    return b'\x0f\x01\x02\x00\x06\x00\x00\x00\xe8\x00\x00\x00'


@pytest.fixture
def ifd_entry_not_offset():
    return b'@\xc6\x03\x00\x03\x00\x00\x00\x00\xb7\x00\x00'


@pytest.fixture
def unknown_tag_ifd_entry():
    return b'\xc5\xc6\x04\x00\x01\x00\x00\x00\x01\x00\x00\x00'


@pytest.fixture
def entry_length_no_offset():
    return b'@\xc6\x03\x00\x02\x00\x00\x00\x02\xb7\x00\x03'


@pytest.fixture
def entry_length_short_value():
    return b'@\xc6\x03\x00\x01\x00\x00\x00\x02\xb7\x00\x03'


def test_ifd_entry_must_have_single_data_source():
    with pytest.raises(TypeError):
        IfdEntry("<")
    with pytest.raises(TypeError):
        IfdEntry("<", blob=1, file=1, offset=1)


def test_new_ifd_entry_from_file(tmpdir, ifd_entry):
    p = tmpdir.realpath().strpath
    with open(os.path.join(p, 'ifd_entry'), mode='w+b') as tmpfile:
        tmpfile.write(ifd_entry)
        tmpfile.seek(0)
        entry = IfdEntry("<", file=tmpfile, tags=tags)
    assert entry.tag_id == 271
    assert entry.tag_name == 'make'
    assert entry.tag_type == 's'
    assert entry.value_len == 6
    assert entry.raw_value == 232


def test_new_ifd_entry_from_blob(ifd_entry):
    entry = IfdEntry("<", blob=ifd_entry, tags=tags)
    assert entry.tag_id == 271
    assert entry.tag_name == 'make'
    assert entry.tag_type == 's'
    assert entry.value_len == 6
    assert entry.raw_value == 232


def test_new_ifd_entry_from_blob_with_offset(ifd_entry):
    entry = IfdEntry("<", blob=(b'\x00' + ifd_entry), offset=1, tags=tags)
    assert entry.tag_id == 271
    assert entry.tag_name == 'make'
    assert entry.tag_type == 's'
    assert entry.value_len == 6
    assert entry.raw_value == 232


def test_new_ifd_no_offset(ifd_entry):
    with pytest.raises(KeyError):
        IfdEntry("<", blob=(b'\x00' + ifd_entry), tags=tags)


def test_unknown_tag_name_should_be_id(unknown_tag_ifd_entry):
    entry = IfdEntry("<", blob=unknown_tag_ifd_entry)
    assert entry.tag_name == 50885


def test_raw_value_not_offset(ifd_entry_not_offset):
    entry = IfdEntry("<", blob=ifd_entry_not_offset)
    assert entry.raw_value == 46848


def test_ifd_entry_no_offset_multi_value(entry_length_no_offset):
    entry = IfdEntry("<", blob=entry_length_no_offset)
    assert entry.raw_value == (46850, 768)


def test_ifd_entry_short_value_seeks_to_end(entry_length_short_value):
    bytesio = BytesIO(entry_length_short_value)
    IfdEntry("<", file=bytesio, rewind=False)
    assert bytesio.tell() == 12
