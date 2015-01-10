from rawphoto.cr2 import Cr2

import pytest


def test_cr2_must_have_single_data_source():
    with pytest.raises(TypeError):
        Cr2("<", blob=1, file=1, offset=1)
