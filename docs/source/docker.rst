.. _docker:

Using Formsender with Docker
============================

Formsender ships with a Dockerfile for easier development. Consult the docker
documentation for instructions on how to use docker: http://docs.docker.com/


Build the Container
-------------------

If you haven't made any changes to the source code, build the containers by
running:

::

   $ docker-compose build


If changes have been made, run:

::

   $ docker-compose build --no-cache

This tells docker to include the updated source code in the build.

Run Formsender in the Container
-------------------------------

Now that the container has been built, you can run the app in the container:

::

   $ docker-compose up

If the original settings in conf.py, Dockerfile, and docker-compose.yml are
unchanged, Formsender will now be running on the docker container's port 5000,
which is bound to the host's port 5000. Forms sent to port 5000 on the host will
communicate with Formsender correctly.
