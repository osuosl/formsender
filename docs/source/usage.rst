.. _usage:

How To Use Formsender
=====================


In conf.py change the following variables to match your setup:

.. code-block:: python

    EMAIL = u'email@example.com'
    TOKN = u'1234567890-='
    CEILING = 10
    DUPLICATE_CHECK_TIME = 3600
    HOST = "0.0.0.0"
    PORT = 5000
    SMTP_HOST = "smtp.osuosl.org"

* ``EMAIL`` is where the form data will be sent.
* ``TOKN`` is the validating token from the form. This must match a hidden field
  in your form called 'tokn'.
* ``CEILING`` is the maximum number of submit requests formsender will accept
  per second.
* ``DUPLICATE_CHECK_TIME`` is the time (in seconds) to check past form
  submissions for duplicate submissions.
* ``HOST`` and ``PORT`` is where the ``run_simple`` listener listens for POST
  requests
* ``SMTP_HOST`` sets the host for the ``sendmail`` function. Must be a smtp
  server

You can run flake8 on request_handler (the application):

.. code-block:: none

    $ make flake


And tests can be run:

.. code-block:: none

    $ make tests

To run the application locally for development purposes:

.. code-block:: none

    $ make run

The app will now wait at ``HOST:PORT`` for the form to be submitted, and
will email the information submitted to the email specified.

You can change the host and port Formsender waits at by modifying the run_simple
method at the bottom of request_handler.py. The first argument is the location
of the listener (set to ``HOST``), the second is the port (set to ``PORT``).
These two arguments can be changed in conf.py to match your desired setup.
