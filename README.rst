=======
Pyaptly
=======

Automates the creation and managment of aptly mirrors and snapshots based on yml
input files.

|pypi| |travis| |coverage| [1]_

.. |pypi| image:: https://badge.fury.io/py/Pyaptly.svg
   :target: https://badge.fury.io/py/Pyaptly
.. |travis|  image:: https://travis-ci.org/adfinis-sygroup/pyaptly.png?branch=master
   :target: https://travis-ci.org/adfinis-sygroup/pyaptly
.. |coverage| image:: https://img.shields.io/badge/coverage-100%25-brightgreen.svg

`Read the Docs`_

.. _`Read the Docs`: https://docs.adfinis-sygroup.ch/public/pyaptly/

.. [1] Coverage enforced by tests (on travis)

Example commands
----------------

Initialize a new aptly server.

.. code:: shell

   pyaptly -c mirrors.yml mirror create
   pyaptly -c mirrors.yml mirror update
   pyaptly -c mirrors.yml snapshot create
   pyaptly -c mirrors.yml publish create

Update mirrors and snapshots and switch publish endpoints with
``automatic-update: true`` to the new snapshots.

.. code:: shell

   pyaptly -c mirrors.yml mirror update
   pyaptly -c mirrors.yml snapshot create
   pyaptly -c mirrors.yml publish create
   pyaptly -c mirrors.yml publish update

Manually trigger a switch to the new snapshots for the publish endpoint
ubuntu/stable.

.. code::

   pyaptly -c mirrors.yml publish update ubuntu/stable

Install Debian/Ubuntu
=====================

Sources:

.. code-block:: text

   deb http://aptly.adfinis-sygroup.ch/adsy-public/debian wheezy main

   deb http://aptly.adfinis-sygroup.ch/adsy-public/debian jessie main

   deb http://aptly.adfinis-sygroup.ch/adsy-public/ubuntu trusty main

   deb http://aptly.adfinis-sygroup.ch/adsy-public/ubuntu vivid main

   deb http://aptly.adfinis-sygroup.ch/adsy-public/ubuntu xenial main

Install:

.. code-block:: bash

   wget -O - http://aptly.adfinis-sygroup.ch/aptly.asc | apt-key add -
   apt-get update
   apt-get install python-pyaptly

Testing
-------

Automatic

.. code:: shell

   git submodule update --init --recursive
   make test-local

Manual. There is a safety check in tests. They won't work if you don't set
$HOME.

.. code:: shell

   git submodule update --init --recursive
   source testenv
   py.test -x

or

.. code:: shell

   git submodule update --init --recursive
   export HOME="$(pwd)"
   export PATH="$HOME/aptly_0.9.6_linux_amd64/:$PATH"
   py.test -x

Vagrant Box
-----------

The box provisions aptly, nginx and two repos which can be used for tests:

.. code::

   aptly mirror create mirro-fakerepo01 http://localhost/fakerepo01 main
   aptly mirror create mirro-fakerepo02 http://localhost/fakerepo02 main
