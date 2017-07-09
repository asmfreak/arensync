# ArEnS

Python3 scripts to ARchive, ENcrypt and Sync (thus `arensync`) files and also to LIst, DEcrypt and EXtract (thus `lideex`). They use Secure SHell (`ssh`), TAR and GNU Privacy Guard (`gpg`) to securely store your files. arensync is widely configure-able. See configuration options below.

arensync depends on Python's standard library, `plumbum` for cool shell combinators and `tqdm` for progress bars.

## Configuration

arensync uses ini-style configuration files. There are 2 types of configuration:
1. Default configuration, loaded before any directory-specific config.
2. Directory-specific configuration, describing a directory to sync.

Both can be specified via arguments. By default scripts use `~/.config/arensync` folder to search for directory-specific `*.conf` files.

Here is an example listing all configuration variables:
```
[DEFAULT]
workdir = /home/vasyapupkin/very-important-docs
tempdir = /tmp
ignorefile = None
user = vasyapupkin
gpgemail = vasyapupkin@some-email-provider.invalid
serveruser = vasyapupkin
server = vasyas.server.host
serverdir = very-important-docs
sshbin = ssh -v
gpgbin = gpg
scpbin = scp
tarbin = tar
```

* `workdir` - local path to sync to server.
* `tempdir` - local path to temporary store archives to be uploaded to server.
* `ignorefile` - git-style ignorefile to use for the directory.
* `user` - local user to sync for (used in configuration validation).
* `gpgemail` - email address for gpg encryption.
* `serveruser`, `server` - user on syncing server ans it's hostname. This `serveruser` MUST have passwordless access to `server`.
* `serverdir` - path on server, where achives for this workdir will be stored.
*  `sshbin`, `gpgbin`, `scpbin`, `tarbin` - paths and optional arguments to utilities. path binary should __NOT__ contain spaces.
