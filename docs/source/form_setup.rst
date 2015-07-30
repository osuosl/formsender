.. _form_setup:

Set Up a Form
=============

To use Formsender, you need to write an html form with several required and
optional fields. Formsender uses these fields to authenticate the form and
format the outgoing email message. To include these fields in your form just
set the ``name``,  ``type``, and ``value`` properties like this:

``<input type="hidden" name="hidden" value=""/>``

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

* **hidden** - must be empty, must be hidden

    example: ``<input type="hidden" name="hidden" value=""/>``

* **tokn** - contents must match TOKN in conf.py, must be hidden

    example: ``<input type="hidden" name="tokn" value="1234567890-=" />``

* **redirect** - url to redirect to on form submission, if an error occurs a
  query string will be added with an error message.

    example: ``<input type="hidden" name="redirect" value="http://www.example.com" />``

Optional Fields
---------------

Formsender uses additional optional fields to help format your outgoing email.
These optional fields are:

* **mail_subject**

    sets outgoing email subject to mail_subject's contents. If mail_subject is
    not included, the subject will default to ``Form Submission``. This should
    be a hidden field.

    example: ``<input type="hidden" name="mail_subject" value="FORM: New Test Submission" />``

* **mail_from**

    sets outgoing email ``From`` field to mail_from's contents. If mail_from is
    not included, the subject will default to ``Form``. This should be a hidden
    field. This field **must not** contain spaces. Everything following a space
    is ignored when sending the email.

    example: ``<input type="hidden" name="mail_from" value="My_Test_Form" />``
