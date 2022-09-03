import mimetypes
import os
import posixpath
import time
from threading import Thread
from functools import wraps


def guess_type(path):
    base, ext = posixpath.splitext(path)
    if ext in extensions_map:
        return extensions_map[ext]
    ext = ext.lower()
    if ext in extensions_map:
        return extensions_map[ext]
    else:
        return extensions_map['']


def check_file(filename, mimetype=None):
    if '.' in filename:
        if mimetype is None:
            return True
        else:
            startswith = False
            endswith = False
            contains = False
            if mimetype.startswith("*"):
                endswith = True
                mimetype = mimetype[1:]
            if mimetype.endswith("*"):
                startswith = True
                mimetype = mimetype[:-1]
            if startswith and endswith:
                contains = True
            guessed_type = guess_type(filename)
            if guessed_type == mimetype:
                return True
            if startswith and guessed_type.startswith(mimetype):
                return True
            if endswith and guessed_type.endswith(mimetype):
                return True
            if contains and mimetype in guessed_type:
                return True
            return False
    else:
        return False


def safe_name(filename):
    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, "")

    return filename


if not mimetypes.inited:
    mimetypes.init()  # try to read system mime.types
extensions_map = mimetypes.types_map.copy()
extensions_map.update({
    '': 'application/octet-stream',  # Default
    '.py': 'text/plain',
    '.c': 'text/plain',
    '.h': 'text/plain',
    '.js': 'text/javascript'
})


def super_replace(s, x):
    for y in x.keys():
        s = s.replace(y, x[y])
    return s


def find(iterable, item):
    for i in range(len(iterable)):
        if item == iterable[i]:
            return i


def in_thread(*, group=None, name=None, daemon=False):
    def deco(func):
        @wraps(func)
        def overwrite(*args, **kwargs):
            t = Thread(target=func, args=args, kwargs=kwargs, group=group, name=name, daemon=daemon)
            t.start()
            return t

        return overwrite

    return deco


@in_thread(daemon=True)
def run_task_later(wait_time, function, args=(), kwargs=None):
    if kwargs is None:
        kwargs = {}
    time.sleep(wait_time)
    function(*args, **kwargs)
