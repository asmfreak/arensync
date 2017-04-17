import os, sys, hashlib
from functools import partial
try:
    from multiprocessing import Pool, cpu_count
    p = Pool()
except ImportError:
    class Pool:
        def __init__(self, *args):
            pass
        def map(self, fcn, arr):
            return map(fcn, arr)
    def cpu_count():
        return 1

#help(pool.map)
#exit()

def blockreader(f, block_size=4096):
    while True:
        b = f.read(block_size)
        if len(b) == 0:
            return
        yield b

def hash(p, hashclass=hashlib.sha256):
    p, lp = p
    with open(p, "rb") as f:
        hash = hashclass()
        for block in blockreader(f):
            hash.update(block)
    return "  ".join((hash.hexdigest(), lp))

path = sys.argv[1]
if not os.path.exists(path):
    print("Path {path} does not exist".format(path=path))
    sys.exit(1)
path = os.path.abspath(path)
pool = Pool(cpu_count())
for dir, dirs, files in os.walk(path):
    ldir = dir.replace(path, ".")
    files = [(os.path.join(dir, f), os.path.join(ldir, f))  for f in files]
    print("\n".join(pool.map(hash, files)))
