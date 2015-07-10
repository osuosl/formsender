.. _usage:
To run:

At the bottom of request_handler.py there is a command called run_simple. The
first variable is the location of the form, the second is the port. Change those
two variables to match your setup. In conf.py there is an email. This is the
email that the form responses will go to. Make sure that this is correct. Once
you have set all variables to the desired values, run this command:

.. code::

    python request_handler.py


The app will now wait for the form to be submitted, and will email the
information submitted to the email specified.
