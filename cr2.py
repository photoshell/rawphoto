import os
import struct

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


class Cr2(object):

    class Header(object):

        def __init__(self, fhandle):
            assert not fhandle.closed
            fhandle.seek(0)
            header_buffer = fhandle.read(16)
            (endianness,) = struct.unpack_from('H', header_buffer)
            if endianness == 0x4949:
                # Intel
                self.endian_flag = '<'
            elif endianness == 0x4D4D:
                # Motorola
                self.endian_flag = '>'
            else:
                # WTF (use native)?
                self.endian_flag = '@'
            raw_header = struct.unpack_from(self.endian_flag + 'HHLHBBL',
                                            header_buffer)
            self.raw_header = raw_header
            self.tiff_magic_word = raw_header[1]
            self.tiff_offset = raw_header[2]
            self.magic_word = raw_header[3]
            self.major_version = raw_header[4]
            self.minor_version = raw_header[5]
            self.raw_ifd_offset = raw_header[6]

    class Ifd(object):

        class IfdEntry(object):

            def __init__(self, num, parent):
                assert not parent.fhandle.closed

                self.parent = parent
                parent.fhandle.seek(parent.offset + 2 + (12 * num))
                buf = parent.fhandle.read(8)
                (self.tag_id, self.tag_type, self.value_len) = struct.unpack_from(
                    parent.endian_flag + 'HHL', buf)
                buf = parent.fhandle.read(4)
                if tag_types[self.tag_type][0] == '*':
                    (self.raw_value,) = struct.unpack_from(parent.endian_flag +
                                                           'L', buf)
                    self.value = -1
                else:
                    (self.raw_value,) = struct.unpack_from(parent.endian_flag +
                                                           tag_types[self.tag_type], buf)
                    self.value = self.raw_value

            def get_value(self):
                # If value is not cached yet, read it
                if self.value == -1:
                    # Read value from file
                    self.parent.fhandle.seek(self.raw_value)
                    buf = self.parent.fhandle.read(self.value_len)
                    tag_fmt = tag_types[self.tag_type][1:]
                    if tag_fmt == 's' or tag_fmt == 'p':
                        tag_fmt = repr(self.value_len) + tag_fmt
                    (self.value,) = struct.unpack_from(
                        self.parent.endian_flag + tag_fmt, buf)
                return self.value

        def __init__(self, offset, parent):
            assert not parent.fhandle.closed

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

    def __init__(self, file_path):
        self.file_path = file_path
        self.fhandle = open(file_path, "rb")
        self.header = self.Header(self.fhandle)
        # TODO: Make IDF array
        self.ifd0 = self.Ifd(16, self)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.fhandle.close()

    def get_endian_flag(self):
        return self.header.endian_flag

    def get_header(self):
        return self.header
