import getpass
from plumbum import local, SshMachine, cli, colors, FG

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
    else:
        return None


class ConfiguredApplication(cli.Application):
    defconfig = cli.SwitchAttr(
        "--default-config", cli.ExistingFile,
        default=local.path("~/.config/arensync/config"),
        help="default config filename",
        envname="ARENSYNC_DEFAULTCONFIG"
    )

    configdir = cli.SwitchAttr(
        "--configdir", cli.ExistingDirectory,
        default=local.path("~/.config/arensync/"),
        help="directory with configs",
        envname="ARENSYNC_CONFIGDIR"
    )

    def default_config(self, config_name):
        with cli.Config(config_name) as config:
            config.get_into(self, "workdir", local.cwd)
            config.get_into(self, "ignorefile", "")
            config.get_into(self, "user", getpass.getuser())
            config.get_into(self, "gpgemail", self.user + "@" + local['hostname']()[:-1])
            config.get_into(self, "serveruser", "")
            config.get_into(self, "server", "")
            config.get_into(self, "serverdir", "")
            config.get_into(self, "sshbin", "ssh")
            config.get_into(self, "gpgbin", "gpg")
            config.get_into(self, "scpbin", "scp")
            config.get_into(self, "tarbin", "tar -v")
            config.get_into(self, "tempdir", "/tmp")

    def config(self, config_name):
        with cli.Config(config_name) as config:
            config.get_from(self, "workdir")
            config.get_from(self, "ignorefile")
            config.get_from(self, "user")
            config.get_from(self, "gpgemail")
            config.get_from(self, "serveruser")
            config.get_from(self, "server")
            config.get_from(self, "serverdir")
            config.get_from(self, "sshbin")
            config.get_from(self, "gpgbin")
            config.get_from(self, "scpbin")
            config.get_from(self, "tempdir")
