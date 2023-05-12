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

   $ docker build -t formsender .


Run Formsender in the Container
-------------------------------

Now that the container has been built, you can run the app in the container:

::

   $ docker run -p 5000:5000

If the original settings in conf.py, Dockerfile, and docker-compose.yml are
unchanged, Formsender will now be running on the docker container's port 5000,
which is bound to the host's port 5000. Forms sent to port 5000 on the host will
communicate with Formsender correctly.
