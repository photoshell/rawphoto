from rawphoto.raw import Raw
from rawphoto.tiff import Header
from rawphoto.tiff import Ifd

tags = {
    0x00fe: 'subfile_type',
    0x0100: 'image_width',
    0x0101: 'image_height',
    0x0102: 'bits_per_sample',
    0x0103: 'compression',
    0x0106: 'photometric_interpretation',
    0x0111: 'data_offset',
    0x0115: 'samples_per_pixel',
    0x0116: 'rows_per_strip',
    0x0116: 'data_length',
    0x011a: 'x_resolution',
    0x011b: 'y_resolution',
    0x011c: 'planar_configuration',
    0x0128: 'resolution_unit',
    0x014a: ('preview_image', 'raw_data'),
    0x0201: 'data_offset',
    0x0202: 'data_length',
    0x0213: 'ycb_cr_positioning',
    0x0214: 'reference_black_white',
    0x828d: 'cfa_repeat_pattern_dim',
    0x828e: 'cfa_pattern_two',
    0x8769: 'exif',
    0x9217: 'sensing_method',
    0x9286: 'user_comment'
}

subdirs = [0x8769, 0x014a]


class Nef(Raw):

    def __init__(self, blob=None, file=None, filename=None):
        super(Nef, self).__init__(blob=blob, file=file, filename=filename)

        pos = self.tell()
        self.header = Header(self.read(8))
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
        """Read a preview image from the NEF as a JPEG."""
        return self._get_image_data(name='preview_image')

    @property
    def thumbnail_image(self):
        raise NotImplementedError("NEF's do not contain a thumbnail image")

    @property
    def uncompressed_full_size_image(self):
        raise NotImplementedError("NEF's do not contain a full sized jpeg")

    @property
    def raw_data(self):
        """Read the raw image data from the NEF."""
        return self._get_image_data(name='raw_data')
