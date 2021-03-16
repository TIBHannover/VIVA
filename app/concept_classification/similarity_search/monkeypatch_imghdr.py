"""
Monkey patch bug in imghdr which causes valid JPEG images to be classified as 'None' type.
"""


def monkeypatch_imghdr():
    """Return additional testing methods to patch the current imghdr instance."""
    return test_small_header_jpeg, test_exif_jfif


def test_small_header_jpeg(h, f):
    """JPEG data with a small header"""
    jpeg_bytecode = b'\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06' \
                    b'\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f'
    if len(h) >= 32 and h[5] == 67 and h[:32] == jpeg_bytecode:
        return 'jpeg'


def test_exif_jfif(h, f):
    """JPEG data in JFIF or Exif format"""
    if h[6:10] in (b'JFIF', b'Exif') or b'JFIF' in h[:23] or h[:2] == b'\xff\xd8':
        return 'jpeg'
