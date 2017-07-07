#!/usr/bin/env python3
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
import datetime
import os
strptime = datetime.datetime.strptime
from plumbum import local, FG, BG, SshMachine
from plumbum import colors
from operator import itemgetter
from itertools import groupby as uniq
import tempfile
flatten = lambda l: [item for sublist in l for item in sublist]

wd = '/home/delphi/camera'
remwd = 'backups/camera'
remuser = 'delphi'
remhost = 'asm.kik.cl'
remote = SshMachine(remhost, user=remuser)
rcat = remote['cat']
rls = remote['ls']
rfind = remote['find'][remwd, '-name', '*.lst']
decrypt = local['gpg']['-d']
extract = local['tar']['xzvf', '-', '-C', wd, '-T']


files = flatten(
    [
        [
            {
                "hash":y[0:64],
                "file":y[65:],
                "archive": x[:-4],
                "date":strptime(x.split("archive")[-1].split('.tar')[0], "%Y%m%d_%H%M%S")
             }  for y in rcat(x).split('\n') if y != ''
         ] for x in rfind().split('\n') if x != ''
])
archived_files = { 
    x:list(map(itemgetter('file'),y)) 
    for x,y in uniq(
        sorted(
            [next(y) for x, y in uniq(
                sorted(
                    files, 
                    key=itemgetter('file','date')
                ), 
                itemgetter('file'))
            ], 
            key=itemgetter('archive')
        ), 
        itemgetter('archive'))
}
for archive, compressed in archived_files.items():
    with tempfile.NamedTemporaryFile(mode="w") as f:
        f.write("\n".join(compressed))
        f.flush()
        job = (rcat[archive+'.gpg'] | decrypt | extract[f.name])
        job = job.popen()
        fcount = len(compressed)
        for line in job.stdout:
            line = line[:-1].decode('utf-8')
            if line in compressed:
                fcount -= 1
                fcount_ = "{:06d}".format(fcount)
                print('Files from {1} to unpack [{0}]'.format(colors.red | fcount_, colors.blue|archive), end='\r')
        if fcount == 0:
            print("Files from {} unpacked  [  {}  ]".format(colors.blue|archive,colors.green | "OK"))
        job.wait()
