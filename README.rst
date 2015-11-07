"""""""
Pyaptly
"""""""

Automates the creation and managment of aptly mirrors and snapshots based on yml
input files.

Example commands
----------------

Initialize a new Aptly server.

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
   pyaptly -c mirrors.yml publish update

Manually trigger a switch to the new snapshots for the publish endpoint
ubuntu/stable.

.. code::

   pyaptly -c mirrors.yml publish update ubuntu/stable

Testing
-------

.. code:: shell

   git submodule update --init --recursive
   make test
