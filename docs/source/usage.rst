.. _usage:

How To Use Formsender
=====================

At the bottom of request_handler.py there is a command called run_simple. The
first variable is the location of the form, the second is the port. Change those
two variables to match your setup.

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

.. code-block:: none

    make run

The app will now wait for the form to be submitted, and will email the
information submitted to the email specified.
