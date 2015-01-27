import os

from io import BytesIO

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


class Raw(object):

    def __init__(self, blob=None, file=None, filename=None):

        if sum([i is not None for i in [file, blob, filename]]) > 1:
            raise TypeError("Raw must specify only one input")

        if file is not None:
            self.fhandle = file
        elif blob is not None:
            self.fhandle = BytesIO(blob)
        elif filename is not None:
            self.fhandle = open(filename, "rb")
        else:
            raise TypeError("Raw must specify at least one input")

    def read(self, *args):
        """Read data from the underlying file handle

        Arguments are passed through to fhandle.read.
        """
        return self.fhandle.read(*args)

    def seek(self, *args):
        """Seek in the underlying file.

        Arguments are passed through to fhandle.seek.
        """
        return self.fhandle.seek(*args)

    def tell(self):
        """Get the current offset in the raw file."""
        return self.fhandle.tell()

    def close(self):
        """Closes the underlying file handle.
        """
        return self.fhandle.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    @property
    def endianness(self):
        try:
            return self.header.endianness
        except AttributeError:
            return "@"

    def _get_image_data(self, num=0, name=None):
        """Gets image data from an IFD or sub-IFD.

        Args:
            name - The sub IFD name to read an image from.
            num - The IFD number to read an image from.
        """

        if name is not None:
            entries = self.ifds[0].subifds[name].entries
        else:
            entries = self.ifds[num].entries
        if 'data_offset' in entries and 'data_length' in entries:
            pos = self.tell()
            self.seek(entries['data_offset'].raw_value)
            img_data = self.read(entries['data_length'].raw_value)
            self.seek(pos)
            return img_data
        else:
            return None
