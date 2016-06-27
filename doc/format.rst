======================
YAML input file format
======================

The yaml file defines the four main components **repo**, **mirror**,
**snapshot** and **publish**.

repo
   is a local repository. PyAptly only creates repositories for you, the rest of
   the interaction with repositories is done via aptly directly.

.. caution::

   You have to add at least one package before you can use a repo in snapshots
   or publishes.

mirror
   mirrors a remote repository. PyAptly creates and updates mirrors. Usually all
   interaction is done through PyAptly

.. caution::

   You have to update a mirror (download packages) at least once befure you can
   use a mirror in snapshots or publishes.

snapshot
   PyAptly supports daily and weekly snapshots. Snapshots are created at a fixed
   time. If PyAptly is called later than that time the snapshot will still have
   the timestamp of the time when I should have been created. This is needed to
   find the snapshots in publishes or merges. Snapshots can also merge multiple
   other snapshots. There are also so called current snapshots, that are always
   updated and republished when PyAptly is run with "snapshot update" or
   "publish update".

publish
   can have **snapshot**, **repo** or **publish** as source. If a publish has a
   current-snapshot as sources it is automatically updated.

.. note::

   Current-snapshots are not the same as timestamped snapshots using
   "current" as timestamp. A current-snapshot has a unique name and is updated
   on every PyAptly run.

Defining a mirror
=================

.. note::

   Every config-key ending in a S expects a list, but the yaml-reader will convert
   the value into a list for you, if you supply a single value.

.. code-block:: yaml

   mirror:
     google-chrome:
       components: "main"
       architectures: ["amd64", "i386"]
       distribution: "stable"
       archive: "http://dl.google.com/linux/chrome/deb/"
       gpg-keys: ["7FAC5991"]
       gpg-urls: ["https://dl.google.com/linux/linux_signing_key.pub"]

components
   main, contrib and non-free are the classical components from Debian. Other
   Repositories may use this to subdivide the repositories in other ways.

architectures
   is another way of subdividing your repository, but should be used accordingly
   usually there is amd64 and i386.

distrubtion
   is a distribution name, e.g. squeeze, for flat repositories use ./ instead of
   distribution name

archive
   is the URL to download from.

gpg-keys
   a list of gpg-keys that are automatically fetched from the key-server before
   the mirror is created.

gpg-urls
   if the keys are not on a public keyserver pyaptly can download them from URLs
   too.

sources
   if sources True pyaptly will tell aptly to also download sources.

udeb
   if set to True use udeb (micro debs) which are stripped down debian packages,
   intended to save disk space.

Defining a snapshot
===================

.. code-block:: yaml

   snapshot:
     google-chrome-stable-%T:
       timestamp: {"time": "00:00", "repeat-weekly": "sat"}
       filter:
         source: {"name": "google-chrome-%T", "timestamp": "current"}
         query: "google-chrome-stable"

The name of a snapshot can include the %T macro, which is replace by the
calculated time of the snapshot.

timestamp
   can contain **time** and **repeat-weekly**. If only **time** is defined it is
   a daily snapshot and is created daily at the given time. If **repeat-weekly**
   is also defined the snapshot will be created only on the given day. Allowed
   values are: 'mon' 'tue' 'wed' 'thu' 'fri' 'sat' 'sun' 

.. code-block:: yaml

    merge:
      - "roche-keyring-latest"
      - {"name": "trusty-main-stable-%T", "timestamp": "current"}

merge
   merges multiple snapshots. It can either be a plain snapshot in this case
   *roche-keyring-latest* or in can be a snapshot. The definition contains the
   name of the snapshot including a %T macro and **timestamp** which defines the
   N latest snapshot. "current" is a name for 0 and "previous" for 1. But you
   can also define any other number.

.. caution::
   
   If the N latest snapshot hasn't been created you will see an error, but
   PyAptly should continue.

.. code-block:: yaml

  google-chrome-stable-%T:
    timestamp: {"time": "00:00", "repeat-weekly": "sat"}
    filter:
      source: {"name": "google-chrome-%T", "timestamp": "current"}
      query: "google-chrome-stable"

filter
   Filters a snapshot using an aptly query. Define the source using the same
   syntax as in merge. The query uses aptly-query-syntax.

Defining a publish
==================

.. code-block:: yaml

   publish:
     icaclient:
       -
         distribution: "latest"
         architectures: ["amd64", "i386"]
         components: "main"
         repo: "icaclient"
         automatic-update: true
         gpg-key: "7FAC5991"

The name of the publish may include slashes: I.e. "ubuntu/latest".

The sources of a publish can be:

repo
   Name of repo defined in the yaml

.. code-block:: yaml

   publish:
     ubuntu/latest:
       -
         distribution: "trusty"
         origin: "Ubuntu"
         architectures: ["amd64", "i386", "source"]
         components: ["main", "restricted", "universe", "multiverse"]
         snapshots:
           - {"name": "trusty-main_roche-keyring-%T", "timestamp": "current"}
           - {"name": "trusty-restricted-%T",         "timestamp": "current"}
           - {"name": "trusty-universe-%T",           "timestamp": "current"}
           - {"name": "trusty-multiverse-%T",         "timestamp": "current"}
         automatic-update: true

snapshots
   A list of snapshots using the same syntax as in merge.

mirror
   Name of a mirror defined in the yaml

These fields are the same as in the mirror definition:

components
   main, contrib and non-free are the classical components from Debian. Other
   Repositories may use this to subdivide the repositories in other ways.

architectures
   is another way of subdividing your repository, but should be used accordingly
   usually there is amd64 and i386.

distrubtion
   is a distribution name, e.g. squeeze, for flat repositories use ./ instead of
   distribution name

Additional fields are:

   origin
      Optional field indicating the origin of the repository, a single line of
      free form text.

   automatic-update
      If automatic-update is false the publish will only be updated if you
      explicitly name it: "pyaptly publish update ubuntu/stable". If you just
      call "pyaptly pulish update", the will stay on the last publish point
      (snapshot).

   gpg-key
      The key must exist in the users gpg-database and if the database has a
      password the gpg-agent must be active and the password must have been
      entered.

      See also gpg-agent.conf:

      default-cache-ttl 31536000  # A Year

      max-cache-ttl 31536000
