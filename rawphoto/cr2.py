from collections import namedtuple
from rawphoto.raw import Raw
from rawphoto.tiff import endian_flags
from rawphoto.tiff import exif_tags
from rawphoto.tiff import Ifd

import struct


_HeaderFields = namedtuple("HeaderFields", [
    "endianness", "raw_header", "tiff_magic_word", "tiff_offset",
    "magic_word", "major_version", "minor_version", "raw_ifd_offset"
])

subdirs = [0x8769]

tags = exif_tags.copy()
tags.update({
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
    0x00b4: 'color_space'  # 1=sRGB, 2=Adobe RGB
})


class Header(_HeaderFields):
    __slots__ = ()

    def __new__(cls, blob=None):
        [endianness] = struct.unpack_from('>H', blob)

        endianness = endian_flags.get(endianness, "@")
        raw_header = struct.unpack(endianness + 'HHLHBBL', blob)

        return super(Header, cls).__new__(cls, endianness, raw_header,
                                          *raw_header[1:])


class Cr2(Raw):

    def __init__(self, blob=None, file=None, filename=None):
        super(Cr2, self).__init__(blob=blob, file=file, filename=filename)

        pos = self.tell()
        self.header = Header(self.read(16))
        self.ifds = []
        self.ifds.append(Ifd(self.endianness, file=self.fhandle, tags=tags,
                             subdirs=subdirs))
        next_ifd_offset = self.ifds[0].next_ifd_offset

        while next_ifd_offset != 0:
            self.seek(next_ifd_offset)
            self.ifds.append(Ifd(self.endianness, file=self.fhandle, tags=tags,
                                 subdirs=subdirs))
            next_ifd_offset = self.ifds[len(self.ifds) - 1].next_ifd_offset

        self.seek(pos)

    @property
    def preview_image(self):
        """Read a quarter sized image as RGB data from the CR2 file."""
        return self._get_image_data()

    @property
    def thumbnail_image(self):
        """Read a thumbnail image from the CR2."""
        return self._get_image_data(num=1)

    @property
    def uncompressed_full_size_image(self):
        """Read uncompressed JPEG data with no WB settings from the CR2."""
        return self._get_image_data(num=2)

    @property
    def raw_data(self):
        """Read the raw image data from the CR2."""
        return self._get_image_data(num=3)
