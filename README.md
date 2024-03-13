# Pyaptly

Automates the creation and managment of aptly mirrors and snapshots based on toml
input files.

**Important**: Corrently under heavy development:

- For for the old version [switch to the master branch](https://github.com/adfinis/pyaptly/tree/master)
- Main branch builds contain [alpha packages](https://github.com/adfinis/pyaptly/actions/runs/8147002919), see Artifacts

## Example commands

Initialize a new aptly server.

```shell
pyaptly -c mirrors.toml mirror create
pyaptly -c mirrors.toml mirror update
pyaptly -c mirrors.toml snapshot create
pyaptly -c mirrors.toml publish create
```

Update mirrors and snapshots and switch publish endpoints with
```automatic-update: true``` to the new snapshots.

```shell
pyaptly -c mirrors.toml mirror update
pyaptly -c mirrors.toml snapshot create
pyaptly -c mirrors.toml publish create
pyaptly -c mirrors.toml publish update
```

Manually trigger a switch to the new snapshots for the publish endpoint
ubuntu/stable.

```shell
pyaptly -c mirrors.toml publish update ubuntu/stable
```

## Debugging

The most interesting mode for users is not `--debug` but `--info` which shows
all commands executed.

```bash
> pyaptly legacy -- --info --config pyaptly/tests/repo.toml repo create
Command call
  cmd:         gpg --no-default-keyring --keyring trustedkeys.gpg --list-keys --with-colons -> 0
  stdout:     'tru::1:1709575833:0:3:1:5
               pub:-:255:22:2841988729C7F3FF:1701882080:::-:::scESC:::::ed25519:::0:
               fpr:::::::::6380C07FF6496016E01CF4522841988729C7F3FF:
               uid:-::::1701882080::5BBE9C7E7AA5EEE3538F66274125D69FA727FD1E::Pyaptly Test 01 <test01@pyaptly.nowhere>::::::::::0:
               sub:-:255:18:0A1CBEF26FE4F36E:1701882080::::::e:::::cv25519::
               fpr:::::::::9EE64E40A5E3530D3E18A97C0A1CBEF26FE4F36E:
               pub:-:255:22:EC54D33E5B5EBE98:1701882297:::-:::scESC:::::ed25519:::0:
               fpr:::::::::660D45228AB6B59CCE48AFB3EC54D33E5B5EBE98:
               uid:-::::1701882297::F3EF71B78669C0FC259A4078151BDC5815A6015D::Pyaptly Test 02 <test02@pyaptly.nowhere>::::::::::0:
               sub:-:255:18:042FE0F5BB743B60:1701882297::::::e:::::cv25519::
               fpr:::::::::AE58B62134E02AF8E5D55FF4042FE0F5BB743B60:'
Command call
  cmd:         aptly repo list -raw -> 0
  stderr:     'Config file not found, creating default config at /root/.aptly.conf'
Command call
  cmd:         aptly mirror list -raw -> 0
Command call
  cmd:         aptly snapshot list -raw -> 0
Command call
  cmd:         aptly publish list -raw -> 0
Command call
  cmd:         aptly repo -architectures=amd64,i386 -distribution=stable -component=main create centrify -> 0
  stdout:     'Local repo [centrify] successfully added.
               You can run 'aptly repo add centrify ...' to add packages to repository.'
```

Commands that fail are always displayed in red on a tty, but that actually only
happens if something is broken.
