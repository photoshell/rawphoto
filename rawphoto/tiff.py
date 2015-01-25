from collections import namedtuple
from io import BytesIO

import struct


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


_IfdEntryFields = namedtuple("IfdEntryFields", [
    "tag_id", "tag_name", "tag_type", "tag_type_key", "value_len", "raw_value"
])


class IfdEntry(_IfdEntryFields):
    __slots__ = ()

    def __new__(cls, endianness, file=None, blob=None, offset=None, tags={},
                tag_types=tag_types):
        if sum([i is not None for i in [file, blob]]) > 1:
            raise TypeError("IfdEntry must only specify one input")

        if file is not None:
            fhandle = file
        elif blob is not None:
            fhandle = BytesIO(blob)
        else:
            raise TypeError("IfdEntry must specify at least one input")

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

    def __init__(self, endianness,
                 file=None, blob=None,
                 offset=None,
                 subdirs=[], tags={}, tag_types=tag_types):
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

        pos = self.fhandle.seek(0, 1)
        if offset is not None:
            self.fhandle.seek(offset)

        self.endianness = endianness
        [num_entries] = _read_tag(endianness + 'H', self.fhandle)

        self.entries = {}
        self.subifds = {}
        buf = self.fhandle.read(12 * num_entries)
        for i in range(num_entries):
            e = IfdEntry(endianness, blob=buf[(12 * i):(12 * (i + 1))],
                         tags=tags)
            self.entries[e.tag_name] = e
            if e.tag_id in subdirs:
                self.subifds[e.tag_name] = Ifd(endianness, file=self.fhandle,
                                               offset=e.raw_value, tags=tags,
                                               subdirs=subdirs)
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
                    # This branch should probably never be hit...
                    value = entry.raw_value

            # Be polite and rewind the file...
            self.fhandle.seek(pos)
            return value
        else:
            # Return existing value
            return entry.raw_value
