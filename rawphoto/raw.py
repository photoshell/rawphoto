import os

from collections import namedtuple
from rawphoto.cr2 import Cr2
from rawphoto import cr2

raw_formats = ['.CR2']


def discover(path):
    """recursively search for raw files in a given directory"""
    file_list = []

    for root, _, files in os.walk(path):
        for file_name in files:
            if os.path.splitext(file_name)[1].upper() in raw_formats:
                file_path = os.path.join(root, file_name)
                file_list.append(file_path)

    return file_list


_Raw = namedtuple("Raw", [
    "raw_format", "fhandle", "metadata"
])


class Raw(_Raw):
    __slots__ = ()

    def __new__(cls, filename=None):
        ext = os.path.splitext(filename)[1].upper()
        if ext not in raw_formats:
            raise TypeError("File format not recognized")
        metadata = {}
        if ext == '.CR2':
            fhandle = Cr2(filename=filename)
            for tag in cr2.tags.values():
                e = fhandle.ifds[0].entries.get(tag)
                if e is not None:
                    metadata[tag] = fhandle.ifds[0].get_value(e)
            raw_format = 'CR2'
        else:
            raise TypeError("File format not recognized")
        metadata = {
            'datetime': metadata.get('datetime', ''),
            'width': metadata.get('image_width', ''),
            'height': metadata.get('image_length', ''),
            'make': metadata.get('make', ''),
            'model': metadata.get('model', ''),
        }

        return super(Raw, cls).__new__(cls, raw_format, fhandle, metadata)

    def __enter__(self):
        return self

    def close(self):
        self.fhandle.close()

    def __exit__(self, type, value, traceback):
        self.close()
