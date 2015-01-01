import os
import struct

from collections import namedtuple

# Mapping from manufacturer to associated endianness as accepted by struct
endian_flags = {
    0x4949: '<',  # Intel
    0x4D4D: '>',  # Motorola
}

_HeaderFields = namedtuple("HeaderFields", [
    "endian_flag", "raw_header", "tiff_magic_word", "tiff_offset",
    "magic_word", "major_version", "minor_version", "raw_ifd_offset"
])

tags = {
    'image_width': 0x0100,
    'image_length': 0x0101,
    'bits_per_sample': 0x0102,
    'compression': 0x0103,
    'make': 0x010f,
    'model': 0x0110,
    'strip_offset': 0x0111,
    'orientation': 0x0112,
    'strip_byte_counts': 0x0117,
    'x_resolution': 0x011a,
    'y_resolution': 0x011b,
    'resolution_unit': 0x0128,
    'datetime': 0x0132,
    'exif': 0x8769,
    'gps_data': 0x8825
}

# Mapping of tag types to format strings.
# Format strings that start with a * are too long to fit in the IFD entry and
# are actually a pointer to somewhere else in the file.
tag_types = {
    0x1: 'B',  # Unsigned char
    0x2: '*s',  # String (with ending 0)
    0x3: 'H',  # Unsigned short
    0x4: 'L',  # Unsigned long
    0x5: '*Q',  # Unsigned rational
    0x6: 'b',  # Signed char
    0x7: '*p',  # Byte sequence
    0x8: 'h',  # Signed short
    0x9: 'l',  # Signed long
    0xA: '*q',  # Signed rational
    0xB: '*f',  # Float (IEEE)
    0xC: '*d',  # Double (IEEE)
}

# Format info: http://lclevy.free.fr/cr2/
# The Cr2 class loads a CR2 file from disk. It is currently read-only.


class Header(_HeaderFields):
    __slots__ = ()

    def __new__(cls, header_bytes):
        [endianness] = struct.unpack_from('H', header_bytes)

        endian_flag = endian_flags.get(endianness, "@")
        raw_header = struct.unpack(endian_flag + 'HHLHBBL', header_bytes)

        return super().__new__(cls, endian_flag, raw_header, *raw_header[1:])


class Cr2():

    class Ifd(object):

        class IfdEntry(object):

            def __init__(self, num, parent):
                self.parent = parent
                parent.fhandle.seek(parent.offset + 2 + (12 * num))
                buf = parent.fhandle.read(8)
                (self.tag_id, self.tag_type, self.value_len) = struct.unpack_from(
                    parent.endian_flag + 'HHL', buf)
                buf = parent.fhandle.read(4)
                if tag_types[self.tag_type].startswith('*'):
                    (self.raw_value,) = struct.unpack_from(parent.endian_flag +
                                                           'L', buf)
                    self._value = -1
                else:
                    (self.raw_value,) = struct.unpack_from(parent.endian_flag +
                                                           tag_types[self.tag_type], buf)
                    self._value = self.raw_value

            @property
            def value(self):
                # If value is not cached yet, read it
                if self._value == -1:
                    # Read value from file
                    self.parent.fhandle.seek(self.raw_value)
                    buf = self.parent.fhandle.read(self.value_len)
                    tag_fmt = tag_types[self.tag_type][1:]
                    if tag_fmt == 's' or tag_fmt == 'p':
                        tag_fmt = repr(self.value_len) + tag_fmt
                    [self._value] = struct.unpack_from(
                        self.parent.endian_flag + tag_fmt, buf)
                    if tag_fmt[-1] == 's':
                        # Decode to UTF-8, removing null terminator.
                        self._value = self._value.decode("utf-8")[:-1]
                return self._value

        def __init__(self, offset, parent):
            self.fhandle = parent.fhandle
            self.offset = offset
            self.endian_flag = parent.get_endian_flag()

            # Read num entries
            parent.fhandle.seek(offset)
            buf = parent.fhandle.read(2)
            (self.num_entries,) = struct.unpack_from(
                parent.get_endian_flag() + 'H', buf)

            # Read next offset
            parent.fhandle.seek(offset + (2 + 12 * self.num_entries))
            buf = parent.fhandle.read(2)
            (self.next_ifd_offset,) = struct.unpack_from(
                parent.get_endian_flag() + 'H', buf)

        def find_entry(self, name):
            for entry_num in range(0, self.num_entries):
                ifd_entry = self.IfdEntry(entry_num, self)

                if ifd_entry.tag_id == tags[name]:
                    return ifd_entry
            return -1

    def __init__(self, file_path):
        self.file_path = file_path
        self.fhandle = open(file_path, "rb")
        self.header = Header(self.fhandle.read(16))
        self.ifd = []
        self.ifd.append(self.Ifd(16, self))
        for i in range(1, 3):
            self.ifd.append(self.Ifd(self.ifd[i - 1].next_ifd_offset, self))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.fhandle.close()

    def get_endian_flag(self):
        return self.header.endian_flag

    def get_header(self):
        return self.header
