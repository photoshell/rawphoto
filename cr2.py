import os
import struct
from io import BufferedReader

from collections import namedtuple

# Mapping from manufacturer to associated endianness as accepted by struct
endian_flags = {
    0x4949: '<',  # Intel
    0x4D4D: '>',  # Motorola
}

_HeaderFields = namedtuple("HeaderFields", [
    "endianness", "raw_header", "tiff_magic_word", "tiff_offset",
    "magic_word", "major_version", "minor_version", "raw_ifd_offset"
])

_IfdEntryFields = namedtuple("IfdEntryFields", [
    "tag_id", "tag_type", "value_len", "raw_value"
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
tag_types = {
    0x1: 'B',  # Unsigned char
    0x2: 's',  # String (with ending \0)
    0x3: 'H',  # Unsigned short
    0x4: 'L',  # Unsigned long
    0x5: 'Q',  # Unsigned rational
    0x6: 'b',  # Signed char
    0x7: 'p',  # Byte sequence
    0x8: 'h',  # Signed short
    0x9: 'l',  # Signed long
    0xA: 'q',  # Signed rational
    0xB: 'f',  # Float (IEEE)
    0xC: 'd',  # Double (IEEE)
}

# Format info: http://lclevy.free.fr/cr2/
# The Cr2 class loads a CR2 file from disk. It is currently read-only.


class Header(_HeaderFields):
    __slots__ = ()

    def __new__(cls, header_bytes):
        [endianness] = struct.unpack_from('>H', header_bytes)

        endianness = endian_flags.get(endianness, "@")
        raw_header = struct.unpack(endianness + 'HHLHBBL', header_bytes)

        return super().__new__(cls, endianness, raw_header, *raw_header[1:])


class IfdEntry(_IfdEntryFields):
    __slots__ = ()

    def __new__(cls, endianness, entry_bytes):
        def unpack_at(tag_type, offset):
            return struct.unpack_from(endianness + tag_type, entry_bytes,
                                      offset)
        tag_id, tag_type_key, value_len = unpack_at('HHL', 0)
        tag_type = tag_types[tag_type_key]
        if struct.calcsize(tag_type) > 4 or tag_type == 's' or tag_type == 'p':
            # If the value is a pointer to something small, read it:
            [raw_value] = unpack_at('L', 8)
        else:
            # If the value is not an offset go ahead and read it:
            [raw_value] = unpack_at(tag_type, 8)

        return super().__new__(cls, tag_id, tag_type, value_len, raw_value)


class Ifd(object):

    def __init__(self, endianness, image_file):
        def read_tag(tag_type):
            buf = image_file.read(struct.calcsize(tag_type))
            return struct.unpack_from(endianness + tag_type, buf)
        self.image_file = image_file
        self.endianness = endianness
        [num_entries] = read_tag('H')

        self.entries = []
        buf = image_file.read(12 * num_entries)
        self.entries = [IfdEntry(endianness,
                                 buf[(12 * i):(12 * (i + 1))]) for i in range(num_entries)]

        [self.next_ifd_offset] = read_tag('H')

    def find_entry(self, name):
        for entry in self.entries:
            if entry.tag_id == tags[name]:
                return entry

    def get_value(self, entry):
        tag_type = entry.tag_type
        if struct.calcsize(tag_type) > 4 or tag_type == 's' or tag_type == 'p':
            # Read value
            pos = self.image_file.seek(0, 1)
            self.image_file.seek(entry.raw_value)
            if tag_type == 's' or tag_type == 'p':
                buf = self.image_file.read(entry.value_len)
                [value] = struct.unpack_from('{}{}'.format(entry.value_len,
                                                           tag_type), buf)
                if tag_type == 's':
                    value = value.rstrip(b'\0').decode("utf-8")
            else:
                buf = self.image_file.read(struct.calcsize(tag_type))
                [value] = struct.unpack_from(self.endianness + tag_type, buf)

            # Be polite and rewind the file...
            self.image_file.seek(pos)
            return value
        else:
            # Return existing value
            return entry.raw_value


class Cr2():

    def __init__(self, image=None, blob=None, file=None, filename=None):

        # TODO: Raise a TypeError if multiple arguments are supplied?
        if file is not None:
            self.fhandle = file
        elif blob is not None:
            self.fhandle = BufferedReader(blob)
        elif filename is not None:
            self.fhandle = open(filename, "rb")

        self.header = Header(self.fhandle.read(16))
        self.ifd = []
        self.ifd.append(Ifd(self.endianness, self.fhandle))
        for i in range(1, 3):
            self.fhandle.seek(self.ifd[i - 1].next_ifd_offset)
            self.ifd.append(Ifd(self.endianness, self.fhandle))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.fhandle.close()

    @property
    def endianness(self):
        return self.header.endianness
