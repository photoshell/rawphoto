from collections import namedtuple
from io import BytesIO

import os
import struct

exif_tags = {
    0x0001: 'interop_index',
    0x0002: 'interop_version',
    0x000b: 'processing_software',
    0x00fe: 'subfile_type',
    0x0100: 'image_width',
    0x0101: 'image_height',
    0x0102: 'bits_per_sample',
    0x0103: 'compression',
    0x0106: 'photometric_interpretation',
    0x010f: 'make',
    0x0110: 'model',
    0x0111: 'data_offset',
    0x0112: 'orientation',
    0x0115: 'samples_per_pixel',
    0x0116: 'row_per_strip',
    0x0117: 'data_length',
    0x011a: 'x_resolution',
    0x011b: 'y_resolution',
    0x011c: 'planar_configuration',
    0x0128: 'resolution_unit',
    0x0132: 'datetime',
    0x0201: 'data_offset',  # Thumbnail
    0x0202: 'data_length',  # Thumbnail
    0x4010: 'custom_picture_style_file_name',
    0x4020: 'ambience_info',
    0x828d: 'cfa_repeat_pattern_dim',
    0x828e: 'cfa_pattern_two',
    0x829a: 'exposure_time',
    0x829d: 'fnumber',
    0x8769: 'exif',
    0x8825: 'gps_data',
    0x927c: 'makernote',
    0xc633: 'shadow_scale',
    0xc634: 'makernote',  # SR2 private, DNG data, makernote pentax, etc.
    0xc635: 'makernote_safety',
    0xc640: 'raw_image_segmentation',
    0xfdea: 'lens',
    0xfe4c: 'raw_file',
    0xfe4d: 'converter',
    0xfe4e: 'white_balance',
    0xfe51: 'exposure',
    0xfe51: 'exposure',
    0xfe52: 'shadows',
    0xfe53: 'brightness',
    0xfe54: 'contrast',
    0xfe55: 'saturation',
    0xfe56: 'sharpness',
    0xfe57: 'smoothness',
    0xfe58: 'moire_filter',
}


# Mapping from manufacturer to associated endianness as accepted by struct
endian_flags = {
    0x4949: '<',  # Intel
    0x4D4D: '>',  # Motorola
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
    0xD: 'L',  # IFD (Unsigned long pointer; always to a child IFD)
}


def _read_tag(tag_type, fhandle):
    """Read and unpack bytes from a file.

    Args:
        tag_type - A struct format string
        fhandle - A file like object to read from
    """
    buf = fhandle.read(struct.calcsize(tag_type))
    return struct.unpack(tag_type, buf)


_HeaderFields = namedtuple("HeaderFields", [
    "endianness", "raw_header", "tiff_magic_word", "first_ifd_offset"
])


class Header(_HeaderFields):
    __slots__ = ()

    def __new__(cls, blob=None):
        [endianness] = struct.unpack_from('>H', blob)

        endianness = endian_flags.get(endianness, "@")
        raw_header = struct.unpack(endianness + 'HHL', blob)

        return super(Header, cls).__new__(cls, endianness, raw_header,
                                          *raw_header[1:])


_IfdEntryFields = namedtuple("IfdEntryFields", [
    "tag_id", "tag_name", "tag_type", "tag_type_key", "value_len", "raw_value"
])


class IfdEntry(_IfdEntryFields):
    __slots__ = ()

    def __new__(cls, endianness, file=None, blob=None, offset=None,
                tags=exif_tags, tag_types=tag_types, rewind=True):
        if sum([i is not None for i in [file, blob]]) > 1:
            raise TypeError("IfdEntry must only specify one input")

        if file is not None:
            fhandle = file
        elif blob is not None:
            fhandle = BytesIO(blob)
        else:
            raise TypeError("IfdEntry must specify at least one input")

        pos = fhandle.tell()
        if offset is not None:
            fhandle.seek(offset)

        tag_id, tag_type_key, value_len = _read_tag(endianness + 'HHL',
                                                    fhandle)
        if tag_id in tags:
            tag_name = tags[tag_id]
        else:
            tag_name = tag_id
        tag_type = tag_types[tag_type_key]
        size = struct.calcsize(tag_type) * value_len
        if size > 4 or tag_type == 's':
            # If the value is a pointer to something small:
            [raw_value] = _read_tag(endianness + 'L', fhandle)
        else:
            # If the value is not an offset go ahead and read it:
            if value_len > 1:
                raw_value = _read_tag('{}{}{}'.format(endianness, value_len,
                                                      tag_type), fhandle)
            else:
                [raw_value] = _read_tag(endianness + tag_type, fhandle)
            # Fast forward to the end of the entry
            if size < 4:
                fhandle.seek(4 - size, os.SEEK_CUR)

        # Rewind the file...
        if rewind:
            fhandle.seek(pos)

        return super(IfdEntry, cls).__new__(cls, tag_id, tag_name, tag_type,
                                            tag_type_key, value_len, raw_value)


class Ifd(object):

    def __init__(self, endianness, file=None, blob=None, offset=None,
                 subdirs=[], tags=exif_tags, tag_types=tag_types):
        if sum([i is not None for i in [file, blob]]) > 1:
            raise TypeError("IFD must only specify one input")

        if file is not None:
            self.fhandle = file
        elif blob is not None:
            self.fhandle = BytesIO(blob)
        else:
            raise TypeError("IFD must specify an input")

        self.tags = tags
        self.subdirs = subdirs
        self.tag_types = tag_types

        pos = self.fhandle.tell()
        if offset is not None:
            self.fhandle.seek(offset)

        self.endianness = endianness
        [num_entries] = _read_tag(endianness + 'H', self.fhandle)

        self.entries = {}
        self.subifds = {}
        for i in range(num_entries):
            e = IfdEntry(endianness, file=self.fhandle,
                         tags=tags, rewind=False)
            self.entries[e.tag_name] = e
            if e.tag_id in subdirs:
                if e.value_len > 1:
                    i = 0
                    for o in self.get_value(e):
                        self.subifds[e.tag_name[i]] = Ifd(endianness,
                                                          file=self.fhandle,
                                                          offset=o, tags=tags,
                                                          subdirs=subdirs)
                        i += 1

                else:
                    self.subifds[e.tag_name] = Ifd(endianness,
                                                   file=self.fhandle,
                                                   offset=e.raw_value,
                                                   tags=tags,
                                                   subdirs=subdirs)
        [self.next_ifd_offset] = _read_tag(endianness + 'H', self.fhandle)
        self.fhandle.seek(pos)

    def get_value(self, entry):
        """Get the value of an entry in the IFD.

        Args:
            entry - The IFDEntry to read the value for.
        """
        tag_type = entry.tag_type
        size = struct.calcsize(self.endianness + tag_type) * entry.value_len
        if size > 4 or tag_type == 's':
            # Read value
            pos = self.fhandle.tell()
            self.fhandle.seek(entry.raw_value)
            if tag_type == 's':
                buf = self.fhandle.read(entry.value_len)
                [value] = struct.unpack('{}{}'.format(entry.value_len,
                                                      tag_type), buf)
                # If this is a null terminated string
                if entry.tag_type_key == 0x02:
                    value = value.rstrip(b'\0').decode("utf-8")
            elif entry.value_len > 1:
                buf = self.fhandle.read(size)
                if len(buf) >= size:
                    value = struct.unpack_from(
                        '{}{}{}'.format(self.endianness, entry.value_len,
                                        tag_type), buf)
                else:
                    # This branch should probably never be hit...
                    value = entry.raw_value
            else:
                buf = self.fhandle.read(size)
                if len(buf) >= size:
                    [value] = struct.unpack_from(
                        self.endianness + tag_type, buf)
                else:
                    # This branch should probably never be hit...
                    value = entry.raw_value

            # Be polite and rewind the file...
            self.fhandle.seek(pos)
            return value
        else:
            # Return existing value
            return entry.raw_value
