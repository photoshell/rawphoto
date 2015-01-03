import os
import struct

from collections import namedtuple
from io import BufferedReader

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
    "tag_id", "tag_name", "tag_type", "value_len", "raw_value"
])

tags = {
    0x0100: 'image_width',
    0x0101: 'image_length',
    0x0102: 'bits_per_sample',
    0x0103: 'compression',
    0x0106: 'photometric_interpretation',
    0x010f: 'make',
    0x0110: 'model',
    0x0111: 'strip_offset',
    0x0112: 'orientation',
    0x0115: 'samples_per_pixel',
    0x0116: 'row_per_strip',
    0x0117: 'strip_byte_counts',
    0x011a: 'x_resolution',
    0x011b: 'y_resolution',
    0x011c: 'planar_configuration',
    0x0128: 'resolution_unit',
    0x0132: 'datetime',
    0x0201: 'thumbnail_offset',
    0x0202: 'thumbnail_length',
    0x829a: 'exposure_time',
    0x829d: 'fnumber',
    0x8769: 'exif',
    0x8825: 'gps_data',
    0x927c: 'makernote',
    0xc640: 'cr2_slice',
}

# Mapping of tag types to format strings.
tag_types = {
    0x1: 'B',  # Unsigned char
    0x2: 's',  # String (with ending \0)
    0x3: 'H',  # Unsigned short
    0x4: 'L',  # Unsigned long
    0x5: 'L',  # Unsigned rational (ignoring second half)
    0x6: 'b',  # Signed char
    0x7: 'p',  # Byte sequence
    0x8: 'h',  # Signed short
    0x9: 'l',  # Signed long
    0xA: 'l',  # Signed rational (ignoring second half)
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
        if tag_id in tags:
            tag_name = tags[tag_id]
        else:
            tag_name = None
        tag_type = tag_types[tag_type_key]
        if struct.calcsize(tag_type) > 4 or tag_type == 's' or tag_type == 'p':
            # If the value is a pointer to something small, read it:
            [raw_value] = unpack_at('L', 8)
        else:
            # If the value is not an offset go ahead and read it:
            [raw_value] = unpack_at(tag_type, 8)

        return super().__new__(cls, tag_id, tag_name, tag_type, value_len, raw_value)


class Ifd(object):

    def __init__(self, endianness, image_file, offset=None):
        def read_tag(tag_type):
            buf = image_file.read(struct.calcsize(tag_type))
            return struct.unpack_from(endianness + tag_type, buf)

        self.image_file = image_file
        pos = self.image_file.seek(0, 1)
        if offset is not None:
            self.image_file.seek(offset)

        self.endianness = endianness
        [num_entries] = read_tag('H')

        self.entries = {}
        self.subifds = {}
        buf = image_file.read(12 * num_entries)
        for i in range(num_entries):
            e = IfdEntry(endianness, buf[(12 * i):(12 * (i + 1))])
            self.entries[e.tag_name] = e
            if e.tag_name == 'exif':
                self.subifds[e.tag_name] = Ifd(endianness, image_file,
                                               e.raw_value)
        [self.next_ifd_offset] = read_tag('H')
        self.image_file.seek(pos)

    def get_value(self, entry):
        tag_type = entry.tag_type
        size = struct.calcsize(tag_type)
        if size > 4 or tag_type == 's' or tag_type == 'p':
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
                buf = self.image_file.read(size)
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
        self.ifds = []
        self.ifds.append(Ifd(self.endianness, self.fhandle))
        for i in range(1, 3):
            self.fhandle.seek(self.ifds[i - 1].next_ifd_offset)
            self.ifds.append(Ifd(self.endianness, self.fhandle))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.fhandle.close()

    @property
    def endianness(self):
        return self.header.endianness
