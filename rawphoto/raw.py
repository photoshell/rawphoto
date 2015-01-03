import os

from rawphoto import cr2

raw_formats = ['.CR2']


def discover(path):
    """recursively search for raw files in a given directory"""
    file_list = []

    for root, _, files in os.walk(path):
        for file_name in files:
            if os.path.splitext(file_name)[1] in raw_formats:
                file_path = os.path.join(root, file_name)
                file_list.append(file_path)

    return file_list


def read_meta(path, file_hash=None):
    # TODO: if file_hash is None, compute it

    file_ext = os.path.splitext(path)[1]

    metadata = {}
    with open(path, 'rb') as file:
        if file_ext.lower() == ".cr2".lower():
            i = cr2.Cr2(file=file)
            for tag in cr2.tags.values():
                e = i.ifds[0].entries.get(tag)
                if e is not None:
                    metadata[tag] = i.ifds[0].get_value(e)
        else:
            # I want this to crash for now
            return None
            # i = wand.Image(file=file)
            # for key, value in i.metadata.items():
            #     if key.startswith('exif:DateTime'):
            #         dt = value
            #     if key.startswith('exif:'):
            #         metadata[key] = value

    # TODO: this is based on low level structure of CR2 files, it should be
    # extracted to rawphoto and generalized.
    return {
        'datetime': metadata.get('datetime', ''),
        'width': metadata.get('image_width', ''),
        'height': metadata.get('image_length', ''),
        'make': metadata.get('make', ''),
        'model': metadata.get('model', ''),
        'file_hash': file_hash,
    }
