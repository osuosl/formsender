.. _usage:

How To Use Formsender
=====================

Formsender is configured through ``conf.py``. Copy the template
(``cp conf.py.dist conf.py``) and adjust it to match your setup. The template
reads secrets and instance-specific values from environment variables and
defines the remaining tunables as plain values:

.. code-block:: python

    import os

    TOKEN = os.environ['TOKEN']
    CEILING = 10
    DUPLICATE_CHECK_TIME = 3600  # seconds
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # bytes
    HOST = "0.0.0.0"
    PORT = 5000
    RECAPTCHA_SECRET = os.environ['RECAPTCHA_SECRET']
    URL = os.environ.get('RT_URL', "https://support.osuosl.org/REST/2.0/")
    RT_TOKEN = os.environ['RT_TOKEN']
    SENTRY_URI = os.environ.get('SENTRY_URI')

Environment variables
---------------------

These must be supplied in the environment Formsender runs in (for example with
``docker run -e``):

* ``TOKEN`` is the shared secret used to authenticate a form submission. It must
  match the hidden ``token`` field in your form. See the
  `form setup documentation`_.
* ``RECAPTCHA_SECRET`` is the reCAPTCHA secret key. Formsender uses it to verify
  the ``g-recaptcha-response`` submitted by the form against Google's
  ``siteverify`` endpoint. Pair it with the reCAPTCHA site key embedded in your
  form.
* ``RT_TOKEN`` is the RT authentication token used to connect to the RT REST2
  API. It belongs to an RT user with permission to create tickets in the target
  queues.
* ``RT_URL`` (optional) overrides the RT REST2 endpoint. It defaults to
  ``https://support.osuosl.org/REST/2.0/``. Setting it lets a single image serve
  a different RT instance, so one container can be run per RT instance.
* ``SENTRY_URI`` (optional) is a Sentry DSN. When set, errors are reported to
  Sentry.

In-file settings
----------------

These are defined directly in ``conf.py`` and can be edited as needed:

* ``CEILING`` is the maximum number of submissions Formsender will accept per
  second before returning a ``Too Many Requests`` error.
* ``DUPLICATE_CHECK_TIME`` is the window (in seconds) over which identical
  submissions are treated as duplicates.
* ``MAX_CONTENT_LENGTH`` is the maximum size (in bytes) of a submitted request
  body, including any file uploads. Larger requests are rejected with a ``413``
  error. Defaults to 10 MiB.
* ``HOST`` and ``PORT`` are the interface and port the development server
  (``make run``) listens on. In production the bind address is set by the WSGI
  server instead (see ``entrypoint.sh``).

Logging
-------

Formsender writes its logs to standard output in the format
``LEVEL formsender: <message>``. Under Docker/Gunicorn these are captured by the
container's log stream. See the `error codes documentation`_ for the messages
Formsender emits.

Set Up A Development Instance
-----------------------------

To set up a development instance, first start a virtual environment like so:

.. code-block:: none

    $ python3 -m venv venv
    $ source venv/bin/activate


Now install the development requirements (these pull in the runtime
requirements plus the lint, test, and docs tooling; the production image
installs only ``requirements.txt``):

.. code-block:: none

    $ pip install -r requirements-dev.txt


Before you run Formsender, copy the contents of ``conf.py.dist`` into a new file
called ``conf.py`` as described above, and export the required environment
variables (``TOKEN``, ``RECAPTCHA_SECRET``, ``RT_TOKEN``).

You can lint the application with flake8:

.. code-block:: none

    $ make flake

Run the test suite (the tests mock all external calls, so no real RT or
reCAPTCHA credentials are needed):

.. code-block:: none

    $ make tests

Run the test suite with a coverage report (enforces full coverage):

.. code-block:: none

    $ make coverage

To run the application locally for development purposes:

.. code-block:: none

    $ make run

The app will now wait at ``HOST:PORT`` for a form to be submitted, and will
create an RT ticket from each valid submission. If you left the conf file
unchanged, this starts the application at ``http://localhost:5000``, ready to
receive POST requests from forms. There are very specific requirements these
forms must adhere to. Instructions on how to set up a form that speaks to
Formsender can be found in the `form setup documentation`_.

Local Form Testing
------------------

An example of a simple form can be found in ``templates/index.html``. If you
open this in your browser, you can use it to POST to the ``PORT`` defined in
``conf.py``. The form redirects to ``http://www.osuosl.org`` on success; change
the ``redirect`` field value to any site you wish. To confirm that tickets are
actually being created, point ``RT_URL`` and ``RT_TOKEN`` at a test RT instance
and watch its queues.

.. _form setup documentation: http://formsender.readthedocs.org/en/latest/form_setup.html
.. _error codes documentation: http://formsender.readthedocs.org/en/latest/errorcodes.html
