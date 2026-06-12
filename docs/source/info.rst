.. _info:

Information
===========

Formsender is a small WSGI application that turns HTML form submissions into RT
tickets. When a form is POSTed to it, Formsender:

#. Validates the submission and screens it for spam and abuse (a hidden honeypot
   field, a shared token, a per-second rate limit, duplicate detection, and a
   reCAPTCHA check).
#. Formats the submitted fields into a readable ticket body.
#. Creates a ticket through the RT REST2 API, attaching any uploaded files and
   populating any RT custom fields the form declares.
#. Redirects the browser back to the form's ``redirect`` URL, adding an error
   code to the query string if the submission was rejected.

By default tickets are created on ``support.osuosl.org``, but the target RT
instance is configurable (via the ``RT_URL`` environment variable), so a single
Formsender image can serve any RT instance by running one container per
instance.

See the :ref:`usage` documentation for configuration, :ref:`form_setup` for how
to build a compatible form, and :ref:`errorcodes` for the error codes and log
messages Formsender produces.
