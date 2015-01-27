import pytest

from rawphoto import raw
from rawphoto.raw import Raw
from rawphoto.cr2 import Cr2
from tests.cr2_test import cr2_bytes
from tests.cr2_test import header_bytes
from tests.ifd_test import ifd_bytes_string_value
from tests.cr2_test import ifd_strip_image


@pytest.fixture
def cr2_file(tmpdir):
    tmpdir.join("file.cr2").write_binary(cr2_bytes)
    return tmpdir.strpath + '/file.cr2'


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


def test_default_endianness(cr2_file):
    r = Raw(file=cr2_file)
    assert r.endianness == "@"


def test_fetching_image_ifd_index_error():
    with Cr2(blob=cr2_bytes) as cr2:
        with pytest.raises(IndexError):
            cr2._get_image_data(num=50)


def test_fetching_image_no_exists():
    with Cr2(blob=header_bytes + ifd_bytes_string_value) as cr2:
        assert cr2._get_image_data(num=0) is None


def test_fetching_image():
    with Cr2(blob=header_bytes + ifd_strip_image) as cr2:
        assert cr2._get_image_data() == b'II' == cr2.preview_image
