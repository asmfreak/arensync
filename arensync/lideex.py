"""
    arensync -- backup and restore using secure (ssh and gpg) methods
    Copyright 2017 Pavel Pletenev <cpp.create@gmail.com>
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
# pylint: disable=C0111,C0112,C1801,W0201,C0330,no-member,invalid-name
import datetime
import tempfile
from operator import itemgetter
from itertools import groupby as uniq

from plumbum import colors
from . import ConfiguredApplication

strptime = datetime.datetime.strptime


def flatten(l):
    return [item for sublist in l for item in sublist]


class lideex(ConfiguredApplication):
    def check_config(self):
        super(lideex, self).check_config()
        self.remls = self.remote['ls']
        self.remfind = self.remote['find'][self.serverdir, '-name', '*.lst']
        self.decrypt = self.gpg['-d']
        self.extract = self.tar['xzvf', '-', '-C', self.workdir, '-T']

    def algorithm(self):
        files = flatten([[{
            'hash': y[0:64].lstrip(' '),
            'file': y[65:].rstrip(' '),
            'archive': x[:-4],
            'date': strptime(
                x.split('archive')[-1].split('.tar')[0],
                '%Y%m%d_%H%M%S')}
            for y in self.remcat(x).split('\n') if y != '']
            for x in self.remfind().split('\n') if x != ''])
        archived_files = {
            x: list(map(itemgetter('file'), y))
            for x, y in uniq(
                sorted(
                    [next(y) for x, y in uniq(
                        sorted(files, key=itemgetter('file', 'date')),
                        itemgetter('file'))],
                    key=itemgetter('archive')
                ),
                itemgetter('archive'))
        }
        for archive, compressed in archived_files.items():
            with tempfile.NamedTemporaryFile(mode='w') as f:
                f.write('\n'.join(compressed))
                f.flush()
                job = (
                    self.remcat[archive + '.gpg'] |
                    self.decrypt | self.extract[f.name])
                job = job.popen()
                fcount = len(compressed)
                for line in job.stdout:
                    line = line[:-1].decode('utf-8')
                    if line in compressed:
                        fcount -= 1
                        fcount_ = '{:06d}'.format(fcount)
                        print(
                            "Files from {1} to unpack [{0}]".format(  # noqa: Q000
                                colors.red | fcount_, colors.blue | archive),
                            end='\r')
                if fcount == 0:
                    print(
                        "Files from {} unpacked  [  {}  ]".format(  # noqa: Q000
                            colors.blue | archive, colors.green | "OK"))  # noqa: Q000
                job.wait()


def main():
    lideex.run()
