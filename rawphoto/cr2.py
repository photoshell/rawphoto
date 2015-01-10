from collections import namedtuple
from io import BytesIO

import struct

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
    "tag_id", "tag_name", "tag_type", "tag_type_key", "value_len", "raw_value"
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
    0x7: 's',  # Byte sequence
    0x8: 'h',  # Signed short
    0x9: 'l',  # Signed long
    0xA: 'l',  # Signed rational (ignoring second half)
    0xB: 'f',  # Float (IEEE)
    0xC: 'd',  # Double (IEEE)
}


def _read_tag(tag_type, fhandle):
    """Read and unpack bytes from a file.

    Args:
        tag_type - A struct format string
        fhandle - A file like object to read from
    """
    buf = fhandle.read(struct.calcsize(tag_type))
    return struct.unpack(tag_type, buf)


class Header(_HeaderFields):
    __slots__ = ()

    def __new__(cls, blob=None):
        [endianness] = struct.unpack_from('>H', blob)

        endianness = endian_flags.get(endianness, "@")
        raw_header = struct.unpack(endianness + 'HHLHBBL', blob)

        return super(Header, cls).__new__(cls, endianness, raw_header,
                                          *raw_header[1:])


class IfdEntry(_IfdEntryFields):
    __slots__ = ()

    def __new__(cls, endianness, file=None, blob=None, offset=0):
        if sum([i is not None for i in [file, blob]]) != 1:
            raise TypeError("IfdEntry must specify file or blob")

        if file is not None:
            fhandle = file
        elif blob is not None:
            fhandle = BytesIO(blob)

        pos = fhandle.seek(0, 1)
        if offset is not None:
            fhandle.seek(offset)

        tag_id, tag_type_key, value_len = _read_tag(endianness + 'HHL',
                                                    fhandle)
        if tag_id in tags:
            tag_name = tags[tag_id]
        else:
            tag_name = tag_id
        tag_type = tag_types[tag_type_key]
        if struct.calcsize(tag_type) > 4 or tag_type == 's':
            # If the value is a pointer to something small:
            [raw_value] = _read_tag(endianness + 'L', fhandle)
        else:
            # If the value is not an offset go ahead and read it:
            [raw_value] = _read_tag(endianness + tag_type, fhandle)
            fhandle.seek(pos)

        # Rewind the file...
        if pos is not None:
            fhandle.seek(pos)

        return super(IfdEntry, cls).__new__(cls, tag_id, tag_name, tag_type,
                                            tag_type_key, value_len, raw_value)


class Ifd(object):

    def __init__(self, endianness, file=None, blob=None, offset=None):
        if sum([i is not None for i in [file, blob]]) != 1:
            raise TypeError("IFD must specify file or blob")

        if file is not None:
            self.fhandle = file
        elif blob is not None:
            self.fhandle = BytesIO(blob)

        pos = self.fhandle.seek(0, 1)
        if offset is not None:
            self.fhandle.seek(offset)

        self.endianness = endianness
        [num_entries] = _read_tag(endianness + 'H', self.fhandle)

        self.entries = {}
        self.subifds = {}
        buf = self.fhandle.read(12 * num_entries)
        for i in range(num_entries):
            e = IfdEntry(endianness, blob=buf[(12 * i):(12 * (i + 1))])
            self.entries[e.tag_name] = e
            if e.tag_id in subdirs:
                self.subifds[e.tag_name] = Ifd(endianness, file=self.fhandle,
                                               offset=e.raw_value)
        [self.next_ifd_offset] = _read_tag(endianness + 'H', self.fhandle)
        if pos is not None:
            self.fhandle.seek(pos)

    def get_value(self, entry):
        """Get the value of an entry in the IFD.

        Args:
            entry - The IFDEntry to read the value for.
        """
        tag_type = entry.tag_type
        size = struct.calcsize(self.endianness + tag_type)
        if size > 4 or tag_type == 's':
            # Read value
            pos = self.fhandle.seek(0, 1)
            self.fhandle.seek(entry.raw_value)
            if tag_type == 's':
                buf = self.fhandle.read(entry.value_len)
                [value] = struct.unpack('{}{}'.format(entry.value_len,
                                                      tag_type), buf)
                # If this is a null terminated string
                if entry.tag_type_key == 0x02:
                    value = value.rstrip(b'\0').decode("utf-8")
            else:
                buf = self.fhandle.read(size)
                if len(buf) >= size:
                    [value] = struct.unpack_from(
                        self.endianness + tag_type, buf)
                else:
                    # TODO: Unsure if this is correct behavior...
                    value = entry.raw_value

            # Be polite and rewind the file...
            self.fhandle.seek(pos)
            return value
        else:
            # Return existing value
            return entry.raw_value


class Cr2():

    def __init__(self, image=None, blob=None, file=None, filename=None):

        if sum([i is not None for i in [file, blob, filename, image]]) != 1:
            raise TypeError("IFD must specify exactly one input")

        # TODO: Raise a TypeError if multiple arguments are supplied?
        if file is not None:
            self.fhandle = file
        elif blob is not None:
            self.fhandle = BytesIO(blob)
        elif filename is not None:
            self.fhandle = open(filename, "rb")

        pos = self.fhandle.seek(0, 1)
        self.header = Header(self.fhandle.read(16))
        self.ifds = []
        self.ifds.append(Ifd(self.endianness, file=self.fhandle))
        next_ifd_offset = self.ifds[0].next_ifd_offset

        while next_ifd_offset != 0:
            self.fhandle.seek(next_ifd_offset)
            self.ifds.append(Ifd(self.endianness, file=self.fhandle))
            next_ifd_offset = self.ifds[len(self.ifds) - 1].next_ifd_offset

        self.fhandle.seek(pos)

    def read(self, *args):
        """Read data from the CR2 file handle

        Arguments are passed through to fhandle.read.
        """
        return self.fhandle.read(*args)

    def close(self):
        """Closes the CR2 file handle.
        """
        return self.fhandle.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    @property
    def endianness(self):
        """The endianness format flag for the CR2 file."""
        return self.header.endianness

    def _get_image_data(self, ifd_num):
        """Gets image data from one of the IFDs.

        Args:
            ifd_num - The IFD to read an image from.
        """
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
        """Read a quarter sized image as RGB data from the CR2 file."""
        return self._get_image_data(0)

    def get_uncompressed_rgb_no_white_balance(self):
        """Read uncompressed RGB data with no WB settings from the CR2."""
        return self._get_image_data(2)

    def get_raw_data(self):
        """Read the raw image data from the CR2."""
        return self._get_image_data(3)

    def get_thumbnail(self):
        """Read a thumbnail image from the CR2."""
        if len(self.ifds) >= 2:
            entries = self.ifds[1].entries
            if 'thumbnail_length' in entries and 'thumbnail_offset' in entries:
                pos = self.fhandle.seek(0, 1)
                self.fhandle.seek(entries['thumbnail_offset'].raw_value)
                img_data = self.fhandle.read(
                    entries['thumbnail_length'].raw_value)
                self.fhandle.seek(pos)
                return img_data
