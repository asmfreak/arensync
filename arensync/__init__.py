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
# pylint: disable=C0111,C0112,C1801,W0201,no-member,invalid-name
# pylint: disable=too-few-public-methods, too-many-instance-attributes
import os
import getpass
from contextlib import contextmanager
from plumbum import local, cli, SshMachine, colors
from .i18n import N_
# patch multiprocessing on weird platfoms (Android)
try:
    from multiprocessing import Pool, cpu_count
    ___pool = Pool()
except ImportError:
    class Pool:
        def __init__(self, *args):
            pass

        def map(self, fcn, arr):  # pylint: disable=R0201
            return map(fcn, arr)

    def cpu_count():
        return 1


def get_from(config, obj, opt):
    try:
        setattr(obj, opt, config[opt])
    except KeyError:
        pass


def get_into(config, obj, opt, default):
    setattr(obj, opt, config.get(opt, default))


cli.Config.get_into = get_into
cli.Config.get_from = get_from


@cli.Predicate
def OptionalFile(f):
    f = local.path(f)
    if f.exists() and f.is_file():
        return f


@contextmanager
def touch_detach(path):
    path.touch()
    try:
        yield
    finally:
        path.delete()


class ConfiguredApplication(cli.Application):
    defconfig = cli.SwitchAttr(
        '--default-config', cli.ExistingFile,
        default=local.path('~/.config/arensync/config'),
        help='default config filename',
        envname='ARENSYNC_DEFAULTCONFIG'
    )

    configdir = cli.SwitchAttr(
        '--configdir', cli.ExistingDirectory,
        default=local.path('~/.config/arensync/'),
        help='directory with configs',
        envname='ARENSYNC_CONFIGDIR'
    )

    def default_config(self, config_name):
        with cli.Config(config_name) as config:
            config.get_into(self, 'workdir', local.cwd)
            config.get_into(self, 'ignorefile', '')
            config.get_into(self, 'user', getpass.getuser())
            config.get_into(
                self, 'gpgemail',
                self.user + '@' + local['hostname']()[:-1])
            config.get_into(self, 'serveruser', '')
            config.get_into(self, 'server', '')
            config.get_into(self, 'serverdir', '')
            config.get_into(self, 'sshbin', 'ssh')
            config.get_into(self, 'gpgbin', 'gpg')
            config.get_into(self, 'scpbin', 'scp')
            config.get_into(self, 'tarbin', 'tar -v')
            config.get_into(self, 'tempdir', '/tmp')

    def config(self, config_name):
        with cli.Config(config_name) as config:
            config.get_from(self, 'workdir')
            config.get_from(self, 'ignorefile')
            config.get_from(self, 'user')
            config.get_from(self, 'gpgemail')
            config.get_from(self, 'serveruser')
            config.get_from(self, 'server')
            config.get_from(self, 'serverdir')
            config.get_from(self, 'sshbin')
            config.get_from(self, 'gpgbin')
            config.get_from(self, 'scpbin')
            config.get_from(self, 'tempdir')

    def check_config(self):
        self.workdir = cli.ExistingDirectory(self.workdir)
        self.ignorefile = OptionalFile(self.ignorefile)
        self.ignored = None
        if self.ignorefile:
            with open(self.ignorefile) as f:
                self.ignored = f.read()
        self.tempdir = cli.ExistingDirectory(self.tempdir)
        test = (self.tempdir / 'test')
        testgpg = (self.tempdir / 'test.gpg')
        test.touch()
        test.delete()
        self.gpgbin = self.gpgbin.split(' ')
        self.gpg = local[self.gpgbin[0]][self.gpgbin[1:]]
        self.encrypt = self.gpg['-r', self.gpgemail, '--encrypt']
        with touch_detach(test):
            self.encrypt(test)
            testgpg.delete()
        self.sshbin = self.sshbin.split(' ')
        self.ssh = local[self.sshbin[0]]
        self.configured_ssh = self.ssh[self.sshbin[1:]]
        self.scpbin = self.scpbin.split(' ')
        self.scp = local[self.scpbin[0]]
        self.configured_scp = self.scp[self.scpbin[1:]]
        self.tarbin = self.tarbin.split(' ')
        self.tar = local[self.tarbin[0]][self.tarbin[1:]]
        self.remote = SshMachine(
            self.server, user=self.serveruser,
            ssh_command=self.ssh, ssh_opts=self.sshbin[1:],
            scp_command=self.scp, scp_opts=self.scpbin[1:])
        self.serverdir = self.remote.path(self.serverdir)
        with touch_detach(self.serverdir / 'test'):
            pass
        self.remcat = self.remote['cat']
        self.pool = Pool(cpu_count())

    # pylint: disable=arguments-differ
    def main(self, optconfig: cli.ExistingFile=None):
        if optconfig is None:
            configs = self.configdir // '*.conf'
        else:
            configs = [optconfig]
        for config in configs:
            print(N_("Using {}").format(colors.green | os.path.basename(config)))  # noqa: Q000
            self.default_config(self.defconfig)
            self.config(config)
            print(N_("Checking configuration sanity"))  # noqa: Q000
            self.check_config()
            self.algorithm()
            print(N_("Success"))  # noqa: Q000
