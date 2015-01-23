import os
import hashlib

from collections import namedtuple
from rawphoto.cr2 import Cr2
from rawphoto import cr2

raw_formats = ['.CR2']


def _hash_file(file_path):
    """Hash a file"""
    hash = hashlib.sha1()

    # TODO: probably block size or something, although if your machine
    # can't hold the whole file in memory you probably can't edit it
    # anyway.
    with open(file_path, 'rb') as f:
        data = f.read()

    hash.update(data)
    return hash.hexdigest()


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
    "fhandle", "metadata"
])


class Raw(_Raw):
    __slots__ = ()

    def __new__(cls, filename=None):
        ext = os.path.splitext(filename)[1].upper()
        if ext not in raw_formats:
            raise TypeError("File format not recognized")
        metadata = {}
        if ext == '.CR2':
            file_hash = _hash_file(filename)
            fhandle = Cr2(filename=filename)
            for tag in cr2.tags.values():
                e = fhandle.ifds[0].entries.get(tag)
                if e is not None:
                    metadata[tag] = fhandle.ifds[0].get_value(e)
        metadata = {
            'datetime': metadata.get('datetime', ''),
            'width': metadata.get('image_width', ''),
            'height': metadata.get('image_length', ''),
            'make': metadata.get('make', ''),
            'model': metadata.get('model', ''),
            'file_hash': file_hash,
        }

        return super(Raw, cls).__new__(cls, fhandle, metadata)

    def __enter__(self):
        return self

    def close(self):
        self.fhandle.close()

    def __exit__(self, type, value, traceback):
        self.close()
