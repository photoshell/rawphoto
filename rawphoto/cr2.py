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

subdirs = [0x8769, 0x927c]

tags = {
    0x0001: 'canon_camera_settings',
    0x0002: 'canon_focal_length',
    0x0004: 'canon_shot_info',
    0x0005: 'canon_panorama',
    0x0006: 'canon_image_type',
    0x0007: 'canon_firmware_version',
    0x0008: 'file_number',
    0x0009: 'owner_name',
    0x000c: 'serial_number',
    0x000d: 'canon_camera_info',  # Here there be monsters.
    0x000e: 'canon_file_length',
    0x000f: 'custom_functions',
    0x0010: 'canon_model_id',
    0x0011: 'canon_movie_info',
    0x0012: 'canon_af_info',
    0x0013: 'thumbnail_image_valid_area',
    0x0015: 'serial_number_format',
    0x001a: 'super_macro',
    0x001c: 'date_stamp_mode',
    0x001d: 'my_colors',
    0x001e: 'firmware_revision',
    0x0023: 'categories',
    0x0024: 'face_detection_1',
    0x0025: 'face_detection_2',
    0x0026: 'canon_af_info_2',
    0x0027: 'contrast_info',
    0x0028: 'image_unique_id',
    0x002f: 'face_detection_3',
    0x0035: 'time_info',
    0x003c: 'canon_af_info_3',
    0x0081: 'raw_data_offset',
    0x0083: 'original_decision_data_offset',
    0x0095: 'lens_model',
    0x0096: 'serial_info',
    0x00ae: 'color_temperature',
    0x00b4: 'color_space',  # 1=sRGB, 2=Adobe RGB
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
    0x4010: 'custom_picture_style_file_name',
    0x4020: 'ambience_info',
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
            tag_name = tag_id
        tag_type = tag_types[tag_type_key]
        if struct.calcsize(tag_type) > 4 or tag_type == 's' or tag_type == 'p':
            # If the value is a pointer to something small, read it:
            [raw_value] = unpack_at('L', 8)
        else:
            # If the value is not an offset go ahead and read it:
            [raw_value] = unpack_at(tag_type, 8)

        return super().__new__(cls, tag_id, tag_name, tag_type, value_len,
                               raw_value)


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
            if e.tag_id in subdirs:
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
                if len(buf) >= size:
                    [value] = struct.unpack_from(
                        self.endianness + tag_type, buf)
                else:
                    # TODO: Unsure if this is correct behavior...
                    value = entry.raw_value

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

        pos = self.fhandle.seek(0, 1)
        self.header = Header(self.fhandle.read(16))
        self.ifds = []
        self.ifds.append(Ifd(self.endianness, self.fhandle))
        next_ifd_offset = self.ifds[0].next_ifd_offset
        while next_ifd_offset != 0:
            self.fhandle.seek(next_ifd_offset)
            self.ifds.append(Ifd(self.endianness, self.fhandle))
            next_ifd_offset = self.ifds[len(self.ifds) - 1].next_ifd_offset
        self.fhandle.seek(pos)

    def read(self, *args):
        return self.fhandle.read(*args)

    def close(self):
        return self.fhandle.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    @property
    def endianness(self):
        return self.header.endianness

    def _get_image_data(self, ifd_num):
        if len(self.ifds) >= ifd_num + 1:
            entries = self.ifds[ifd_num].entries
            if 'strip_offset' in entries and 'strip_byte_counts' in entries:
                pos = self.fhandle.seek(0, 1)
                self.fhandle.seek(entries['strip_offset'].raw_value)
                img_data = self.fhandle.read(
                    entries['strip_byte_counts'].raw_value)
                self.fhandle.seek(pos)
                return img_data

    def get_quarter_size_rgb(self):
        return self._get_image_data(0)

    def get_uncompressed_rgb_no_white_balance(self):
        return self._get_image_data(2)

    def get_raw_data(self):
        return self._get_image_data(3)

    def get_thumbnail(self):
        if len(self.ifds) >= 2:
            entries = self.ifds[1].entries
            if 'thumbnail_length' in entries and 'thumbnail_offset' in entries:
                pos = self.fhandle.seek(0, 1)
                self.fhandle.seek(entries['thumbnail_offset'].raw_value)
                img_data = self.fhandle.read(
                    entries['thumbnail_length'].raw_value)
                self.fhandle.seek(pos)
                return img_data
