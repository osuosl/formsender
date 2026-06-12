.. _form_setup:

Set Up a Form
=============

To use Formsender, you need to write an html form with several required and
optional fields. Formsender uses these fields to authenticate the form and
format the resulting RT ticket. To include these fields in your form just
set the ``name``,  ``type``, and ``value`` properties like this:

``<input type="hidden" name="last_name" value=""/>``

Required Fields
---------------

To use Formsender, you need to write an html form with several required fields.
Formsender uses these fields to attempt to authenticate the form (make sure it
is not from a robot).

Include required fields by setting the ``name`` property to the following:

* **email** - must contain a valid email on submission. This address becomes the
  ticket's RT Requestor.

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

* **g-recaptcha-response** - a valid reCAPTCHA response token. Formsender
  verifies it server-side against Google's ``siteverify`` endpoint using the
  ``RECAPTCHA_SECRET`` setting. This field is produced automatically by the
  reCAPTCHA widget, so including the widget in your form is enough:

    .. code-block:: html

      <div class="g-recaptcha" data-sitekey="your-recaptcha-site-key"></div>
      <script src="https://www.google.com/recaptcha/api.js" async defer></script>

Optional Fields
---------------

Formsender uses some additional optional fields to help format and route the
resulting ticket:

* **mail_subject_prefix** and **mail_subject_key**

    sets the RT ticket subject based on the contents of these fields. If both
    fields are available and ``mail_subject_key`` contains a valid field name
    for another field in the form, the ticket subject will be formatted as
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

    If neither field is available or valid, the ticket subject will be set to
    the default:

        'Form Submission'

    ``mail_subject_prefix`` and ``mail_subject_key`` should both be hidden
    fields

    example:

    .. code-block:: html

      <input type="hidden" name="mail_subject_prefix" value="Hosting Request" />
      <input type="hidden" name="mail_subject_key" value="project" />
      <input type="text" name="project" value="" size="60" maxlength="128" />

    If the user sets the project field to "Linux Foundation" the ticket subject
    will be ``Hosting Request: Linux Foundation``

* **send_to**

    sets the queue in RT that the ticket will be created in. This should be a
    string that matches an existing queue on your RT instance. If send_to is not
    included, the queue will default to the ``General`` queue. This string
    is case sensitive, and should be a hidden field.

    example: ``<input type="hidden" name="send_to" value="QueueName" />``

    Note that the string, 'QueueName', will map to its corresponding RT queue.

* **custom_fields**

    maps form fields onto RT custom fields. The value is a comma-separated list
    of ``CustomFieldName:form_field`` pairs. For each pair, the value of
    ``form_field`` is sent to the RT custom field ``CustomFieldName``, and that
    form field is left out of the ticket body to avoid duplication. A field that
    appears more than once (such as a checkbox group) is sent as a list, which
    suits multi-value custom fields. This should be a hidden field.

    .. code-block:: html

      <input type="hidden" name="custom_fields"
             value="CompanyName:company,WorkingGroups:workgroups" />
      <input type="text" name="company" value="" />
      <input type="checkbox" name="workgroups" value="Hardware" />
      <input type="checkbox" name="workgroups" value="Software" />

    The RT user identified by ``RT_TOKEN`` must have permission to set the named
    custom fields on tickets in the target queue.

* **fields_to_join**

    Sets a field that joins other fields' values with colons. The value of the
    form must be names of existing fields joined by "," (comma). If the value
    contains field's name that does not exist, an error is returned.

    If the "fields_to_join_name" field is not specified, the joined value will
    be under title "Fields To Join". If it is specified, the joined value will
    be under the title of specified value. For more information, please read the
    "fields_to_join_name" section.

    example: ``<input type="hidden" name="fields_to_join" value="email,project,name" />``

    result section of the ticket body:

    .. code-block:: html

      Fields To Join:
      example@email.com:hosting:John Doe

* **fields_to_join_name**

    Sets the title of the "fields_to_join" value in the ticket body. If not
    specified, the joined value from "fields_to_join" will be under the title
    "Fields To Join". If it is specified, the joined value will be under the
    title of the specified value.

    example:

    .. code-block:: html

      <input type="hidden" name="fields_to_join" value="email,project,name" />
      <input type="hidden" name="fields_to_join_name" value="Description" />

    result section of the ticket body:

    .. code-block:: html

      Description:
      example@email.com:hosting:John Doe

All Other Fields
----------------

Any field that is not one of the special fields above (and is not mapped to a
custom field) is included in the ticket body. Formsender formats the body like
so::

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
ticket body. All following fields are placed in alphabetical order by the input
``name``. Formsender formats each input ``name`` to title case and uses it as a
heading in the body. **Make sure these name fields are descriptive** and do not
use strange formatting like the following:

.. code-block:: html

  <input type="text" name="submitted[distribution]" value="" />

Formsender does not know how to interpret this name and will result in a
``Bad Request`` error from the server.

File Uploads
------------

Any ``<input type="file">`` field is attached to the resulting RT ticket. For
files to be uploaded, the form must be submitted with the
``multipart/form-data`` enctype:

.. code-block:: html

  <form action="https://formsender.example.org" method="post" enctype="multipart/form-data">
    ...
    <input type="file" name="attachment" />
    ...
  </form>

Each uploaded file is sent to RT with its original filename and content type, so
binary files (PDFs, archives, images) are preserved intact. Empty file inputs
are ignored. The combined request size, including all uploads, is limited by the
``MAX_CONTENT_LENGTH`` setting (see the usage documentation).
