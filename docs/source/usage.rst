.. _usage:

How To Use Formsender
=====================

In ``conf.py.dist`` there are several settings that Formsender relies on. To use
these settings copy them to a new ``conf.py file`` in the application's root
directory. You can change the following variables to match your setup:

.. code-block:: python

    EMAIL = {'default': 'email@example.com',
             'example': 'email@example.com',
             'another': 'another_email@example.com'}
    TOKN = u's0m3T0k3n$tr1ng'
    CEILING = 10
    DUPLICATE_CHECK_TIME = 3600
    HOST = "0.0.0.0"
    PORT = 5000
    SMTP_HOST = "smtp.osuosl.org"
    FROM = "formsender@osuosl.org"
    LOG_ADDR = '/dev/log'

* ``EMAIL`` is a dictionary of emails. It contains the different email addresses
  to which the form creator can send an email. This will be set in an optional
  ``send_to`` field on the form. If the user decides not to include/fill out the
  ``send_to`` field, an email should be sent to 'default'.
* ``TOKN`` is the validating token from the form. This must match a hidden field
  in your form called 'tokn'. You can find and set the ``TOKN`` variable in your
  conf.py file. Just make sure you also set the hidden ``tokn`` field value to
  match.
* ``CEILING`` is the maximum number of submit requests formsender will accept
  per second.
* ``DUPLICATE_CHECK_TIME`` is the time (in seconds) to check past form
  submissions for duplicate submissions.
* ``HOST`` and ``PORT`` is where the ``run_simple`` listener listens for POST
  requests
* ``SMTP_HOST`` sets the host for the ``sendmail`` function. Must be a smtp
  server
* ``FROM`` is the address the email will be sent from
* ``LOG_ADDR`` specifies where the formsender logs will be sent. This must point
  to where syslog is listening on your server/workstation.

Set Up A Development Instance
-----------------------------

To set up a development instance, first start a virtual environment like so:

.. code-block:: none

    $ virtualenv venv
    $ source venv/bin/activate


Now install the requirements:

.. code-block:: none

    $ pip install -r requirements.txt


Before you run Formsender, you must copy the contents of ``conf.py.dist`` into a
new file called ``conf.py`` as described above.

You can run flake8 on request_handler (the application):

.. code-block:: none

    $ make flake

Once a valid conf.py file exists, tests can be run:

.. code-block:: none

    $ make tests

To run the application locally for development purposes:

.. code-block:: none

    $ make run

The app will now wait at ``HOST:PORT`` for the form to be submitted, and will
email the information submitted to the email specified. ``HOST`` and ``PORT``
can be changed in ``conf.py`` to match your desired setup. If you left the conf
file unchanged, this will start the application running locally at
``http://localhost:5000`` and can be sent POST requests from
forms. There are very specific requirements these forms must adhere to.
Instructions on how to set up a form that speaks to Formsender can be found in
the `form setup documentation`_.

Local Form Testing
------------------

An example of a simple form can be found in ``templates/index.html``. If you
open this in your browser, you can use that to POST a form to ``PORT`` defined
in ``conf.py``. The form currently redirects to http://www.osuosl.org but you
can change the ``redirect`` field value to any site you wish. To see if your
setup is actually sending an email, change the ``EMAIL`` setting in ``conf.py``
to your personal address.

.. _form setup documentation: http://formsender.readthedocs.org/en/latest/form_setup.html
