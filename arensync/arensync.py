#!env python3
"""Copyright 2017 Pavel Pletenev <cpp.create@gmail.com>
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import os, getpass, glob
from contextlib import contextmanager
from operator import itemgetter as by
from itertools import groupby, chain
import os, sys, hashlib
from functools import partial
from fnmatch import fnmatch
import tempfile

from . import ConfiguredApplication, OptionalFile
from tqdm import tqdm
from plumbum import local, SshMachine, cli, colors, FG
from plumbum.cli.terminal import Progress as P

# patch multiprocessing on weird platfoms (Android)
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



@contextmanager
def touch_detach(path):
    path.touch()
    try:
        yield
    finally:
        path.delete()

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
    return dict(hash=hash.hexdigest(), file=lp)

def uuniq(arr, key):
    y = [ list(y) for x,y in groupby(arr, key) ]
    return [ x[0] for x in y if len(x)==1 ]

def uniq(arr, key):
    return [next(y) for x,y in groupby(arr, key)]

def non_repetative(y):
    y = list(y)
    if len(y)==0:
       return y[0]

def diff_files(arr1, arr2):
    temp = sorted(chain(arr1, arr2, arr2), key=by("file"))
    return uuniq(temp, by("file"))

class arensync(ConfiguredApplication):
    def check_config(self):
        self.workdir = cli.ExistingDirectory(self.workdir)
        self.ignorefile = OptionalFile(self.ignorefile)
        self.ignored = None
        if self.ignorefile:
            with open(self.ignorefile) as f:
                self.ignored = f.read()
        self.tempdir = cli.ExistingDirectory(self.tempdir)
        test = (self.tempdir / "test")
        testgpg = (self.tempdir / "test.gpg")
        test.touch()
        test.delete()
        self.gpgbin = self.gpgbin.split(" ")
        self.gpg = local[self.gpgbin[0]][self.gpgbin[1:]]
        self.encrypt = self.gpg["-r", self.gpgemail, "--encrypt"]
        with touch_detach(test):
            self.encrypt(test)
            testgpg.delete()
        self.sshbin = self.sshbin.split(" ")
        self.ssh = local[self.sshbin[0]]
        self.configured_ssh = self.ssh[self.sshbin[1:]]
        self.scpbin = self.scpbin.split(" ")
        self.scp = local[self.scpbin[0]]
        self.configured_scp = self.scp[self.scpbin[1:]]
        self.tarbin = self.tarbin.split(" ")
        self.tar = local[self.tarbin[0]][self.tarbin[1:]]
        self.remote = SshMachine(
            self.server, user=self.serveruser,
            ssh_command=self.ssh, ssh_opts=self.sshbin[1:],
            scp_command=self.scp, scp_opts=self.scpbin[1:])
        self.serverdir = self.remote.path(self.serverdir)
        with touch_detach(self.serverdir / "test"):
            pass
        self.remcat = self.remote["cat"]
        self.pool = Pool(cpu_count())

    def filter_ignored(self, fl):
        if self.ignored is None:
            return fl
        for f,ff in fl:
            for i in self.ignored:
                if fnmatch(f, i):
                    continue
            yield f,ff

    def get_server_files(self):
        if(len(self.remote["ls"](self.serverdir)[:-1].split("\n"))<=1):
            serverfiles = []
        else:
            serverfiles = [
                {"hash":line[0:64].rstrip(' '),"file":line[65:].lstrip(' ')}
                for lst in  sorted(tqdm(self.serverdir // "*.lst"), reverse=True)
                for line in self.remcat(lst).split("\n")
               if line!=""
            ]
            serverfiles = uniq(sorted(serverfiles, key=by("file")), by("file"))
        return serverfiles

    def get_local_files(self):
        localfiles = []
        for dir, dirs, files in tqdm(os.walk(self.workdir)):
            ldir = dir.replace(self.workdir, ".")
            localfiles.extend(self.pool.map(
                hash,
                tuple(self.filter_ignored((os.path.join(dir, f), os.path.join(ldir, f))
                for f in files))
            ))
        return localfiles

    def do_upload(self):
        serverfiles = self.get_server_files()
        localfiles = self.get_local_files()
        to_upload = diff_files(localfiles, serverfiles)
        for x in to_upload:
            print(colors.green | x["file"])
        if len(to_upload)==0:
            print(colors.red | "Files unchanged. Nothing new to upload.")
            return
        archive = local["date"]["+archive%Y%m%d_%H%M%S.tar.gz"]()[:-1]
        archivepath = self.tempdir / archive
        archivelist = self.tempdir / (archive + ".lst")
        localarchivegpg =  archive + ".gpg"
        archivegpg = self.tempdir / localarchivegpg
        archivegpgsum = self.tempdir / (archive + ".gpg.sum")
        with open(archivelist, "w") as f:
            f.write("\n".join(["{hash} {file}".format(**x) for x in to_upload]))
        with tempfile.NamedTemporaryFile(mode="w") as f:
            f.write("\n".join(map(by("file"), to_upload)))
            f.flush()
            self.tar["cvzf", archivepath, "-C", self.workdir, "-T", f.name] & FG()
        self.encrypt(archivepath)
        with local.cwd(self.tempdir):
            (local["sha256sum"][localarchivegpg] > archivegpgsum)()
        archivepath.delete()
        self.remote.upload(archivelist, self.serverdir)
        self.remote.upload(archivegpg, self.serverdir)
        self.remote.upload(archivegpgsum, self.serverdir)
        with self.remote.cwd(self.serverdir):
            self.remote["sha256sum"]("-c", archive + ".gpg.sum")
        archivelist.delete()
        archivegpg.delete()
        archivegpgsum.delete()

    def main(self):
        for config in self.configdir // "*.conf":
            print("Using {}".format(colors.green | config))
            self.default_config(self.defconfig)
            self.config(config)
            print("Checking configuration sanity")
            self.check_config()
            print("Finding chaged files and uploading to server")
            self.do_upload()
            print("Success")

if __name__ == "__main__":
    arensync.run()
