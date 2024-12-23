# Getting Started

> Note: This tutorial assumes basic knowledge of [Aptly](https://www.aptly.info/).

Pyaptly is capable of managing mirrors, snapshots and publishes.
Each of those are handled completely separately, so it's possible to only a subset with pyaptly.
But for the purpose of this tutorial we assume a clean [install of Aptly](https://www.aptly.info/download/) with no content yet.

TODO: Note to jump to the relevant chapter if only a subset should be managed by aptly.

## Installation

TODO (once packages are available)

## Aptly Mirror

Pyaptly can create and update mirrors. Since mirrors are nor a very complicated construct, there's no extra logic not available within aptly.
Configuring a mirror with pyaptly is pretty much the same as writing a command for aptly - except that it's declarative.
Let's take the following `aptly` commands as an example to creating an aptly mirror:

```bash
gpg --yes --no-default-keyring --keyring trustedkeys.gpg --keyserver keyserver.ubuntu.com --recv-keys EE727D4449467F0E
aptly mirror create aptly "http://repo.aptly.info/" nightly main
```

After adding the gpg key to our keyring, we add a the official `aptly` repository. A pyaptly configuration would look like this:

```toml
[mirror.aptly]
archive = "http://repo.aptly.info/"
gpg-keys = [ "EE727D4449467F0E" ]
keyserver = "keyserver.ubuntu.com"
components = "main"
distribution = "nightly"
```

With this configuration the mirror can be created with the following command line:
```bash
pyaptly mirror ./config.toml create
```

As you can see we more or less just put the command line arguments into the configuration file.
Pyaptly also takes care of downloading the gpp key if it isn't availble yet. If you don't want pyaptly to fetch the gpg key, just omit the variables.

> For a list of all configuration options of a mirror, check out [the reference](TODO: Reference link).

### updating mirrors

We can also tell pyaptly to update all defined mirrors:
```bash
pyaptly mirror ./config.toml update
```

This is exactly the same as `aptly mirror update aptly` with the above config.
But it will update all defined mirrors if more than one is defined, making it a bit more convenient than using `aptly` directly.

## Snapshots

### Basic snapshots

Pyaptly has some extra features for snapshots, but let's start by creating a very simple snapshot first.

```toml
[snapshot."aptly"]
mirror = "aptly"
```
And create the snapshot:
```shell-session
$ pyaptly snapshot ./config.toml create 
$ aptly snapshot list
List of snapshots:
 * [aptly]: Snapshot from mirror [aptly]: http://repo.aptly.info/ nightly
```

An equal aptly command would be:
```bash
aptly snapshot create aptly from mirror aptly
```

This snapshot can now be updated by with pyaptly:
```shell-session
$ pyaptly snapshot ./config.toml update
$ aptly snapshot list
List of snapshots:
 * [aptly]: Snapshot from mirror [aptly]: http://repo.aptly.info/ nightly
 * [aptly-rotated-20240102T1315Z]: Snapshot from mirror [aptly]: http://repo.aptly.info/ nightly
```
As you see, `pyaptly` first "rotates" the snapshot by just renaming and postfixing it with a date. Afterwards, it creates a new snapshot `aptly` which is now up-to-date.

> Similar to mirrors, pyaptly allows a variety of configuration options for snapshots. Check out [the reference](TODO: Link to reference).

### Snapshots with retention

Snapshots with retention are a bit more complicated than simple snapshots.
The retention time is either 1 day or 1 week. Other types of retention are currently not implemented.
Another specialty is that the retention is always the "maximum allowed" retention.
Let's use a daily snapshot as an example:

```toml
[snapshot."aptly-%T"]
mirror = "aptly"

[snapshot."aptly-%T".timestamp]
time = "00:00"
# Uncomment for weekly retention starting on saturday
#repeat-weekly = "mon"
```

Now let's pretend today is January 2 2024 and we don't have a snapshot yet. This is what happens:

```shell-session
$ pyaptly snapshot config.toml create
$ aptly snapshot list -raw # list snapshot names
aptly-20240102T0000Z
$ aptly snapshot show aptly-20240101T0000Z
Name: aptly-20240102T0000Z
Created At: 2024-01-02 13:55:41 UTC
Description: Snapshot from mirror [aptly]: http://repo.aptly.info/ nightly
Number of packages: 173
Sources:
  aptly [repo]
$
```

You will notice that the timestamp in the name is different than the timestamp after `Created At`.
The idea here is simple: We want to create one new Snapshot per *day*.
If it's been already past midnight (our defined `time` of `00:00`), create a snapshot and "backdate" it to this time. If a snapshot with this timestamp already exists, do nothing.
It's crucial to understand that we don't want to create a new snapshot "24 hours later than the previous one". We truly want one in each 24h window.
This is matches the typical use case of usual maintenance windows much more.
For example if Company A patches their servers every day at 20:00, it might makes sense to set `time = 19:00` in the config and run a cronjob at 19:05 to create a new snapshot.
At the same time it's much easier to implement in `pyaptly` this way. We can just generate the name a new snapshot would get, check if this snapshot exists and if it does, we do nothing.
This means if we rerun the same command `pyaptly snapshot config.toml create` a second time 5 minutes later it will do nothing, because the snapshot already exists.

It's also important to understand that `pyaptly snapshot config.toml update` will do nothing, as these snapshots with retention are considered "readonly".

If we were to patch our systems only once a week, then what we want is to uncomment the line `repeat-weekly: "mon"`. This way, our snapshot would be backdated a full day to `aptly-20240102T0000Z`.
This means that pyaptly would only create a new snapshot once a week, no matter how often the command has run.

## Publish

Pyaptly publishes also come with some extra sugar building on the features of the snapshots. But let's start with a simple publish again:
```bash
aptly publish snapshot aptly aptly
```

This could be achieved with the following toml file in pyaptly:
```toml
[publish]
[[publish.aptly]]
distribution = "nightly"
components = "main"
#automatic-update = true
[[publish.aptly.snapshots]]
name = "aptly"
```

First we define a publish called `aptly`. Then - as pyaptly currently can't figure that out itself - we specify the distribution and components.
The last line says which snapshot we want to use.

Afterwards we run:
```shell-session
$ pyaptly publish pyaptly/publish.toml create -n aptly
$ aptly publish show nightly aptly
Prefix: aptly
Distribution: nightly
Architectures: amd64
Sources:
  main: aptly [snapshot]
$
```

It's important that we specify `-n aptly` here. If we want to publish it every time we run the `pyaptly publish` command, we need to uncomment the line `automatic-update = true`
