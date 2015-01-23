import pytest

from rawphoto import raw
from rawphoto.raw import Raw
from tests.cr2_test import cr2_bytes


def test_hash_sha1(tmpdir):
    tmpdir.join('file.test').write("Test")
    assert (raw._hash_file(tmpdir.strpath + '/file.test') ==
            '640ab2bae07bedc4c163f679a746f7ab7fb5d1fa')


def test_discover_must_be_recursive(tmpdir):
    tmpdir.join("file1.CR2").write("")
    tmpdir.mkdir("sub").join("file2.CR2").write("")
    assert len(raw.discover(tmpdir.strpath)) == 2


def test_discover_must_be_case_insensitive(tmpdir):
    tmpdir.join("file1.CR2").write("")
    tmpdir.join("file2.Cr2").write("")
    tmpdir.join("file3.cR2").write("")
    tmpdir.join("file4.cr2").write("")
    assert len(raw.discover(tmpdir.strpath)) == 4


def test_discover_must_ignore_unsupported_extensions(tmpdir):
    tmpdir.join("file.abc").write("")
    assert len(raw.discover(tmpdir.strpath)) == 0


def test_filename_not_stringtype():
    with pytest.raises(AttributeError):
        Raw(None)


def test_unrecognized_format_raises_type_error():
    with pytest.raises(TypeError):
        Raw('file.ABC')


def test_cr2_is_supported(tmpdir):
    tmpdir.join("file.cr2").write_binary(cr2_bytes)
    with Raw(filename=(tmpdir.strpath + '/file.cr2')) as raw:
        assert 'file_hash' in raw.metadata
        assert (raw.metadata['file_hash'] ==
                '72ada310f7ff4b84d974d62f2c72fc870889f682')
