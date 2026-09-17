"""Small OS boundaries shared by native Windows and container installations."""
from contextlib import contextmanager
import os
from pathlib import Path


def openshot_command(script, *args):
    return [os.getenv('OPENSHOT_PYTHON', '/usr/bin/python3'),
            str(Path(__file__).with_name(script)), *map(str, args)]


@contextmanager
def exclusive_file_lock(path):
    with open(path, 'a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0, 2)
            if handle.tell() == 0:
                handle.write(b'\0')
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def mock_font_filter():
    # A relative font shipped in the native working directory avoids FFmpeg's
    # drive-letter/backslash escaping rules. Linux retains its system font.
    return os.getenv('MOCK_FONT', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
