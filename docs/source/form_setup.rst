.. _form_setup:

Set Up a Form
=============

To use Formsender, you need to write an html form with several required and
optional fields. Formsender uses these fields to authenticate the form and
format the outgoing email message. To include these fields in your form just
set the ``name``,  ``type``, and ``value`` properties like this:

``<input type="hidden" name="last_name" value=""/>``

Required Fields
---------------

To use Formsender, you need to write an html form with several required fields.
Formsender uses these fields to attempt to authenticate the form (make sure it
is not from a robot).

Include required fields by setting the ``name`` property to the following:

* **email** - must contain a valid email on submission

    example: ``<input type="text" name="email" value="" size="60" maxlength="128" />``

* **name** - cannot be empty on submission

    example: ``<input type="text" name="name" value="" size="60" maxlength="128" />``

* **last_name** - not for an actual last name field. Must be empty, must be
  hidden

    example: ``<input type="hidden" name="last_name" value=""/>``

* **tokn** - contents must match TOKN in conf.py, must be hidden

    example: ``<input type="hidden" name="tokn" value="s0m3T0k3n$tr1ng" />``

* **redirect** - url to redirect to on form submission, if an error occurs a
  query string will be added with an error message. Should be hidden.

    example: ``<input type="hidden" name="redirect" value="http://www.example.com" />``

Optional Fields
---------------

Formsender uses an additional optional field to help format your outgoing
email:

* **mail_subject**

    sets outgoing email subject to mail_subject's contents. If mail_subject is
    not included, the subject will default to ``Form Submission``. This should
    be a hidden field.

    example: ``<input type="hidden" name="mail_subject" value="FORM: New Test Submission" />``

All Other Fields
----------------

Formsender formats the email like so::

    Contact:
    --------
    NAME:   Submitted Name
    EMAIL:   email@example.com

    Information:
    ------------
    Community Size:

    About 15 developers

    Deployment Timeframe:

    Within 7 days

    Distribution:

    Fedora

    Duration Of Need:

    Six months

The contact information, name and email, is placed at the beginning of the
email. All following fields are placed in alphabetical order by the input
``name``. Formsender formats each input ``name`` to title case and uses it as
titles in the email. **Make sure these name fields are descriptive** and do not
use strange formatting like the following:

.. code-block:: html

  <input type="text" name="submitted[distribution]" value="" />

Formsender does not know how to interpret this name and will result in a
``Bad Request`` error from the server.
