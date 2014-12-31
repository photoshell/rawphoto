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


# Format info: http://lclevy.free.fr/cr2/
# The Cr2 class loads a CR2 file from disk. It is currently read-only.
class Cr2(object):

    class Header(object):

        def __init__(self, fhandle):
            if fhandle.closed:
                return
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

    def __init__(self, file_path):
        self.file_path = file_path
        self.fhandle = open(file_path, "rb")
        self.header = self.Header(self.fhandle)

        # Number of entries in IFD0
        self.fhandle.seek(16)
        buf = self.fhandle.read(2)
        (num_entries,) = struct.unpack_from(self.header.endian_flag + 'H', buf)
        self.num_entries = num_entries

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.fhandle.close()

    def get_endianness(self):
        return self.header.endianness

    def get_header(self):
        return self.header

    def get_idf_entry(self, entry_num):
        # TODO: Figure out how much to read... 1024 is not enough.
        buf = self.fhandle.read(1024)
        return self.IdfEntry(struct.unpack_from(
            self.header.endian_flag + 'HHLL', buf,
            self.header.ifd_offset + 2 + entry_num * 12))

    def find_idf_entry(self, name):

        for entry_num in range(0, num_entries):
            idf_entry = self.get_idf_entry(entry_num)

            if idf_entry.tag_id == tags[name]:
                return idf_entry
