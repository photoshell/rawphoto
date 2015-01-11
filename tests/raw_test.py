from rawphoto import raw


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
