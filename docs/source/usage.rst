.. _usage:

How To Use Formsender
=====================


In conf.py change the following variables to match your setup:

.. code-block:: python

    EMAIL = u'email@example.com'
    TOKN = u'1234567890-='
    CEILING = 10

* ``EMAIL`` is where the form data will be sent.
* ``TOKN`` is the validating token from the form. This must match a hidden field
  in your form called 'tokn'.
* ``CEILING`` is the maximum number of submit requests formsender will accept
  per second.

To run the application locally for development purposes:

.. code-block:: none

    make run

The app will now wait at ``localhost:5000`` for the form to be submitted, and
will email the information submitted to the email specified. You can navigate to
``localhost:5000`` to see a simple test form.

If you want to make changes to the local development setup, there is a command
called run_simple at the bottom of request_handler.py. The first variable is the
location of the listener (set to ``127.0.0.1``, or ``localhost``), the second is
the port (set to ``5000``). These two variables can be changed to match your
desired setup.
