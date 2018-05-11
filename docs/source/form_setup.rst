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

* **token** - contents must match TOKEN in conf.py, must be hidden

    example: ``<input type="hidden" name="token" value="s0m3T0k3n$tr1ng" />``

* **redirect** - url to redirect to on form submission, if an error occurs a
  query string will be added with an error message. Should be hidden.

    example: ``<input type="hidden" name="redirect" value="http://www.example.com" />``

Optional Fields
---------------

Formsender uses some additional optional fields to help format your outgoing
email:

* **mail_subject_prefix** and **mail_subject_key**

    sets outgoing email subject based on the contents of these fields. If both
    fields are available and ``mail_subject_key`` contains a valid field name
    for another field in the form, the email subject will be formatted as
    follows (note that ``mail_subject_key`` sets the subject to the contents of
    the user input in the field with a name matching the value in
    ``mail_subject_key``):

        form['mail_subject_prefix']: form[form['mail_subject_key']
        example: Hosting Request: Linux Foundation

    If only ``mail_subject_prefix`` is available and valid:

        form['mail_subject_prefix']
        example: Hosting Request

    If only ``mail_subject_key`` is available and valid:

        form[form['mail_subject_key']]
        example: Linux Foundation

    If neither field is available or valid, the email subject will be set to
    the default:

        'Form Submission'

    ``mail_subject_prefix`` and ``mail_subject_key`` should both be hidden
    fields

    example:

    .. code-block:: html

      <input type="hidden" name="mail_subject_prefix" value="Hosting Request" />
      <input type="hidden" name="mail_subject_key" value="project" />
      <input type="text" name="project" value="" size="60" maxlength="128" />

    If the user sets the project field to "Linux Foundation" the mail subject
    will be ``Hosting Request: Linux Foundation``

* **send_to**

    sets email recipient to send_to's contents. This should be a string that
    matches a key in the email dictionary found in conf.py. If send_to is not
    included, the recipient will default to the ``default`` of the email dict.
    This should be a hidden field.

    example: ``<input type="hidden" name="send_to" value="another" />``

    Note that the string, 'another', will map to its corresponding email.

* **mail_from**

    sets email sender to mail_from's contents. This should be either a valid
    email or the string 'default_from' (matching the dictionary found in
    conf.py). If mail_from is not included in the form, the address will
    default to ``from_default`` of the email dict. This should be a hidden
    field.

    example: ``<input type="hidden" name="mail_from" value="randouser@example.org" />``

* **fields_to_join**

    Sets a field that joins other fields' values with colons. The value of the
    form must be names of existing fields joined by "," (comma). If the value
    contains field's name that does not exist, an error is returned.

    If the "fields_to_join_name" field is not specified, the joined value will
    be under title "Fields To Join". If it is specified, the joined value will
    be under the title of specified value. For more information, please read the
    "fields_to_join_name" section.

    example: ``<input type="hidden" name="fields_to_join" value="email,project,name" />``

    result section of email:

    .. code-block:: html

      Fields To Join:
      example@email.com:hosting:John Doe

* **fields_to_join_name**

    Sets the title name of "fields_to_join" field in the email. If not specified,
    the joined value from "fields_to_join" field will be under title "Field To Join".
    If it is specified, the joined value will be under the title of specified value.

    example:

    .. code-block:: html

      <input type="hidden" name="fields_to_join" value="email,project,name" />
      <input type="hidden" name="fields_to_join_name" value="Description" />

    result section of email:

    .. code-block:: html

      Description:
      example@email.com:hosting:John Doe

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
