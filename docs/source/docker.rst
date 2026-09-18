.. _docker:

Using Formsender with Docker
============================

Formsender ships with a ``Dockerfile`` and is distributed as a container image,
which is the recommended way to deploy it. The image runs the application under
Gunicorn (see ``entrypoint.sh``). Consult the docker documentation for general
usage: https://docs.docker.com/


Use the Published Image
-----------------------

Released images are published to the GitHub Container Registry. To pull and run
the latest image:

::

   $ docker pull ghcr.io/osuosl/formsender:master
   $ docker run -p 5000:5000 \
       -e TOKEN=s0m3T0k3n \
       -e TURNSTILE_SECRET=your-turnstile-secret \
       -e RT_TOKEN=your-rt-token \
       -e RT_URL=https://support.example.org/REST/2.0/ \
       ghcr.io/osuosl/formsender:master

``TOKEN``, ``RT_TOKEN``, and at least one captcha secret (``TURNSTILE_SECRET``,
``ALTCHA_HMAC_KEY`` or ``RECAPTCHA_SECRET``) are required. ``RT_URL`` is
optional and defaults to ``https://support.osuosl.org/REST/2.0/``; set it to
point a container at a different RT instance. ``SENTRY_URI``,
``CAPTCHA_ALLOWED_HOSTNAMES`` and ``TRUSTED_PROXY_COUNT`` are also optional.
See the :ref:`usage` documentation for the full list of settings.

Two settings matter when more than one container serves the same site: set
``TRUSTED_PROXY_COUNT=1`` behind a reverse proxy so the captcha provider sees
the sender's IP address, and give every container the same
``ALTCHA_HMAC_KEY``, because a container cannot verify a challenge another one
signed.


Build the Container
-------------------

To build the image from a local checkout (for example to test source changes):

::

   $ docker build -t formsender .


Run Your Local Build
--------------------

Run the image you just built the same way as the published one:

::

   $ docker run -p 5000:5000 \
       -e TOKEN=s0m3T0k3n \
       -e TURNSTILE_SECRET=your-turnstile-secret \
       -e RT_TOKEN=your-rt-token \
       formsender

Formsender will be listening on the container's port 5000, bound to the host's
port 5000. Forms POSTed to port 5000 on the host will be handled by Formsender.
